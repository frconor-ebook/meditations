#!/usr/bin/env python3
"""Build static semantic 'Related Meditations' using Gemini Embeddings.

Reads the standardized source markdown corpus (same parsing/hold rules as
process_markdown.py), strips standard opening/closing meditation prayers so
embeddings capture each meditation's unique theme, caches vectors in
data/embeddings_cache.json (gitignored) keyed by content SHA-256, and writes
precomputed top-K cosine neighbors to data/semantic_related.json.

Usage:
    python3 build_semantic_related.py               # incremental (only new/changed)
    python3 build_semantic_related.py --force       # re-embed entire corpus
    python3 build_semantic_related.py --dry-run     # show how many files need embedding
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

from process_markdown import (
    load_blocked_slugs,
    make_slug,
    remove_duplicate_title_lines,
    sanitize_title,
)

MODEL_NAME = "models/gemini-embedding-2"
OUTPUT_DIM = 768
TASK_TYPE = "SEMANTIC_SIMILARITY"
TOP_K_STORED = 8
MAX_CHARS = 28000  # Well under gemini-embedding-2's 8,192-token limit
BATCH_SIZE = 12

# Standard closing prayers / proofreader signatures shared by almost every meditation
_CLOSING_PATTERNS = (
    "i thank you, my god",
    "in the name of the father",
    "my immaculate mother",
)


def strip_boilerplate_for_embedding(title, content_lines):
    """Return clean Title + body text with shared opening/closing prayers removed."""
    paragraphs = [line.strip() for line in content_lines if line.strip()]

    def is_opening_boilerplate(p):
        low = p.lower()
        if low.startswith("by fr"):
            return True
        if p.strip("*() ").lower() == "proofread":
            return True
        if p.startswith("*") and p.endswith("*"):
            return True
        return False

    def is_closing_boilerplate(p):
        stripped = p.strip("*() \t")
        low = stripped.lower()
        if any(pat in low for pat in _CLOSING_PATTERNS):
            return True
        # Short trailing proofreader initials like *OLV*, *EW*, *MVF*, *JOSH*
        if p.startswith("*") and p.endswith("*") and re.fullmatch(r"[A-Za-z0-9./\- ]{1,12}", stripped):
            return True
        return False

    # Trim opening boilerplate
    start = 0
    while start < len(paragraphs) and is_opening_boilerplate(paragraphs[start]):
        start += 1

    # Trim closing boilerplate
    end = len(paragraphs)
    while end > start and is_closing_boilerplate(paragraphs[end - 1]):
        end -= 1

    body = "\n\n".join(paragraphs[start:end])
    # Strip markdown emphasis markers for cleaner tokenization
    body = re.sub(r"[*_]+", "", body)
    body = re.sub(r"[ \t]+", " ", body).strip()

    text = f"Title: {title}\n\n{body}"
    if len(text) > MAX_CHARS:
        # Keep opening, middle, and conclusion if a future talk is unusually long
        third = MAX_CHARS // 3
        mid = len(text) // 2
        text = (
            text[:third]
            + "\n\n[...]\n\n"
            + text[mid - third // 2 : mid + third // 2]
            + "\n\n[...]\n\n"
            + text[-third:]
        )
    return text


def content_hash(model, dim, text):
    h = hashlib.sha256()
    h.update(f"{model}|{dim}|{TASK_TYPE}\n".encode("utf-8"))
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def load_corpus(source_dir, data_dir):
    """Parse source markdown files using the exact same slug/hold rules as process_markdown."""
    blocked_slugs = load_blocked_slugs(data_dir)
    meditations = []
    slug_sources = {}

    for filename in sorted(os.listdir(source_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(source_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        title_line_index = -1
        for i, line in enumerate(lines):
            if line.rstrip("\r\n").lstrip().startswith("#"):
                title_line_index = i
                break
        if title_line_index == -1:
            continue

        title = sanitize_title(lines[title_line_index].rstrip("\r\n").lstrip("# ").strip())
        slug = make_slug(title)
        if not slug or slug in blocked_slugs:
            continue

        if slug in slug_sources:
            meditations = [m for m in meditations if m["slug"] != slug]
        slug_sources[slug] = filename

        content_lines = remove_duplicate_title_lines(lines[title_line_index + 1 :], title)
        embed_text = strip_boilerplate_for_embedding(title, content_lines)
        meditations.append(
            {
                "slug": slug,
                "title": title,
                "embed_text": embed_text,
                "sha256": content_hash(MODEL_NAME, OUTPUT_DIM, embed_text),
            }
        )

    meditations.sort(key=lambda m: m["slug"])
    return meditations


def load_cache(cache_path):
    if not os.path.exists(cache_path):
        return {"model": MODEL_NAME, "dim": OUTPUT_DIM, "entries": {}}
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("model") != MODEL_NAME or data.get("dim") != OUTPUT_DIM:
        return {"model": MODEL_NAME, "dim": OUTPUT_DIM, "entries": {}}
    return data


def save_json_atomic(path, payload, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(payload, f, separators=(",", ":"))
        else:
            json.dump(payload, f, indent=2)
    os.replace(tmp, path)


def _parse_retry_delay(exc):
    """Extract server-suggested retry delay (seconds) from a 429 error, if present."""
    msg = str(exc)
    m = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", msg)
    if m:
        return float(m.group(1))
    m = re.search(r"retryDelay['\"]?:\s*['\"]([0-9]+(?:\.[0-9]+)?)s", msg)
    if m:
        return float(m.group(1))
    return None


def embed_batch(client, texts, max_retries=25):
    """Call Gemini embed_content with server-aware rate-limit backoff."""
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.models.embed_content(
                model=MODEL_NAME,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=TASK_TYPE,
                    output_dimensionality=OUTPUT_DIM,
                ),
            )
            return [[round(float(v), 6) for v in emb.values] for emb in resp.embeddings]
        except Exception as exc:
            if attempt == max_retries:
                raise
            suggested = _parse_retry_delay(exc)
            if suggested is not None:
                wait = min(suggested + 1.5, 65.0)
                print(
                    f"  Rate limit (Free Tier TPM) — pausing {wait:.1f}s before retry {attempt}/{max_retries}...",
                    flush=True,
                )
            else:
                wait = delay
                delay = min(delay * 2.0, 30.0)
                print(
                    f"  Retry {attempt}/{max_retries} after {type(exc).__name__}; sleeping {wait:.1f}s...",
                    file=sys.stderr,
                    flush=True,
                )
            time.sleep(wait)


def compute_semantic_neighbors(meditations, entries, top_k=TOP_K_STORED):
    """Compute L2-normalized cosine similarity matrix and return top-K neighbors per slug."""
    slugs = [m["slug"] for m in meditations]
    mat = np.array([entries[s]["vector"] for s in slugs], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat /= norms

    sims = mat @ mat.T
    np.fill_diagonal(sims, -np.inf)

    k = min(top_k, max(0, len(slugs) - 1))
    related = {}
    for i, slug in enumerate(slugs):
        row = sims[i]
        # Stable descending sort by (score, -slug) for deterministic tie-breaking
        top_indices = np.argsort(-row, kind="mergesort")[:k]
        related[slug] = [
            {"slug": slugs[j], "score": round(float(row[j]), 4)}
            for j in top_indices
            if np.isfinite(row[j])
        ]
    return related


def resolve_api_key(script_dir):
    for env_path in (
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "preprocessing_scripts", ".env"),
    ):
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
    return os.environ.get("GEMINI_API_KEY")


def main():
    parser = argparse.ArgumentParser(
        description="Compute static semantic Related Meditations via Gemini Embeddings."
    )
    parser.add_argument("--force", "-f", action="store_true", help="Re-embed all meditations")
    parser.add_argument("--dry-run", action="store_true", help="Show pending work without calling API")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Texts per API call")
    parser.add_argument("--top-k", type=int, default=TOP_K_STORED, help="Neighbors stored per slug")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(os.path.dirname(script_dir), "transcript_proofread_std_markdown")
    data_dir = os.path.join(script_dir, "data")
    cache_path = os.path.join(data_dir, "embeddings_cache.json")
    output_path = os.path.join(data_dir, "semantic_related.json")

    meditations = load_corpus(source_dir, data_dir)
    cache = load_cache(cache_path)
    entries = {} if args.force else dict(cache.get("entries", {}))

    active_slugs = {m["slug"] for m in meditations}
    # Prune deleted/blocked slugs from cache
    pruned = [s for s in entries if s not in active_slugs]
    for s in pruned:
        del entries[s]

    to_embed = [
        m for m in meditations
        if m["slug"] not in entries or entries[m["slug"]].get("sha256") != m["sha256"]
    ]

    print(
        f"Semantic embeddings ({MODEL_NAME}, dim={OUTPUT_DIM}): "
        f"{len(meditations)} meditations, {len(meditations) - len(to_embed)} cached, "
        f"{len(to_embed)} to embed.",
        flush=True,
    )
    if pruned:
        print(f"  Pruned {len(pruned)} removed/blocked slug(s) from cache.", flush=True)

    if args.dry_run:
        return

    if to_embed:
        api_key = resolve_api_key(script_dir)
        if not api_key:
            print(
                "ERROR: GEMINI_API_KEY not found in environment, .env, or preprocessing_scripts/.env",
                file=sys.stderr,
            )
            sys.exit(1)

        client = genai.Client(api_key=api_key)
        t0 = time.time()
        total = len(to_embed)
        already = len(meditations) - total
        for start in range(0, total, args.batch_size):
            batch = to_embed[start : start + args.batch_size]
            vectors = embed_batch(client, [m["embed_text"] for m in batch])
            for m, vec in zip(batch, vectors):
                entries[m["slug"]] = {"sha256": m["sha256"], "vector": vec}

            # Checkpoint after every batch so progress is always resumable
            save_json_atomic(
                cache_path,
                {"model": MODEL_NAME, "dim": OUTPUT_DIM, "entries": entries},
                compact=True,
            )

            done = min(start + len(batch), total)
            overall = already + done
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            pct = 100.0 * overall / len(meditations)
            print(
                f"  Embedded {overall}/{len(meditations)} ({pct:.1f}%) "
                f"[{elapsed:.0f}s elapsed, ~{eta:.0f}s left]",
                flush=True,
            )
    elif pruned or not os.path.exists(cache_path):
        save_json_atomic(
            cache_path,
            {"model": MODEL_NAME, "dim": OUTPUT_DIM, "entries": entries},
            compact=True,
        )

    related = compute_semantic_neighbors(meditations, entries, top_k=args.top_k)
    payload = {
        "model": MODEL_NAME,
        "dim": OUTPUT_DIM,
        "task_type": TASK_TYPE,
        "top_k": args.top_k,
        "count": len(related),
        "related": related,
    }
    save_json_atomic(output_path, payload, compact=False)
    print(f"Wrote {output_path} ({len(related)} meditations, top-{args.top_k} neighbors each).")


if __name__ == "__main__":
    main()
