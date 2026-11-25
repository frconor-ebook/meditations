#!/usr/bin/env python3
"""Mine all Fr. Conor Donnelly meditations for cinematic YouTube short-film stories.

Scans the full corpus with Gemini 2.5 Flash (structured JSON, thinking disabled for
speed/cost) calibrated to the benchmark of 'Doctor, Don't Let Me Die' (from
'The End of Life'): vivid eyewitness anecdotes, true stories, and dramatic parables
with strong visual settings, a memorable spoken line, and universal human appeal.

Incremental SHA-256 cache in data/film_stories_cache.json (gitignored) ensures
unchanged meditations are never re-scanned.

Outputs:
  - data/film_candidates.json       (all extracted stories, ranked)
  - data/TOP_30_FILM_STORIES.md     (curated production shortlist)

Usage:
    python3 mine_film_stories.py                  # incremental run across all 608
    python3 mine_film_stories.py --workers 8      # adjust concurrency
    python3 mine_film_stories.py --limit 10       # test on first 10 uncached
    python3 mine_film_stories.py --force          # rescan entire corpus
"""
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from build_semantic_related import (
    load_corpus,
    resolve_api_key,
    save_json_atomic,
)

MODEL_NAME = "models/gemini-2.5-flash"
PROMPT_VERSION = "v1"
SITE_BASE = "https://frconor-ebook.github.io/meditations/homilies"


class StoryScores(BaseModel):
    emotional_punch: int = Field(ge=1, le=10)
    visualizability: int = Field(ge=1, le=10)
    universal_appeal: int = Field(ge=1, le=10)
    standalone_clarity: int = Field(ge=1, le=10)


class FilmStoryCandidate(BaseModel):
    story_title: str = Field(description="Short internal label, e.g. 'Dublin Night-Duty Doctor (1975)'")
    youtube_title_idea: str = Field(
        description="Compelling, dignified, universal YouTube short-film title (NEVER mention Fr. Conor's name)"
    )
    category: str = Field(
        description="One of: first_person_true_story, eyewitness_anecdote, historical_saint_story, modern_parable"
    )
    era_and_setting: str = Field(description="Concrete visual place & time, e.g. '1975 Dublin hospital at night'")
    teaser_line: str = Field(
        description="Exact verbatim spoken line or punchy sentence from the text for a 2-3s cold open"
    )
    opening_anchor: str = Field(description="Exact verbatim first 10-15 words where the story begins")
    closing_anchor: str = Field(description="Exact verbatim last 10-15 words where the story ends")
    approx_word_count: int = Field(description="Approximate word count of the story segment in the transcript")
    summary: str = Field(description="2-3 sentence narrative arc: setup, turning point, emotional takeaway")
    visual_beats: list[str] = Field(description="4 to 6 concrete visual shots (setting, action, lighting)")
    scores: StoryScores


class MeditationExtraction(BaseModel):
    stories: list[FilmStoryCandidate] = Field(
        default_factory=list,
        description="0 to 3 standout cinematic stories/anecdotes from this meditation. Empty if none qualify.",
    )


SYSTEM_INSTRUCTION = """You are a documentary short-film producer mining Catholic meditation transcripts
for standalone 1.5-to-3-minute cinematic narrative short films for YouTube.

Gold-standard benchmark (score 9-10):
In "The End of Life", the narrator recalls being a young doctor on night duty in a Dublin hospital,
called to a private nursing home where a wealthy man dying of cancer sends his family out, grips the
doctor's wrist with a cold clammy hand, and says in terror: "Doctor, don't let me die."

What qualifies as a strong candidate:
- A CONCRETE, SELF-CONTAINED story with real people, a physical setting, and an emotional turning point
  (e.g., personal medical/pastoral encounters, true stories about ordinary people, vivid historical/saint
  episodes, or striking modern parables).
- Rich visual scenes (hospitals, trains, classrooms, deathbeds, storms, family tables, quiet gestures)
  that work with Fr. Conor's real voiceover over cinematic visuals.
- Universal human resonance (works even for non-Catholic/secular YouTube viewers; NEVER include
  "Fr. Conor" or "Father Conor" in youtube_title_idea).

What does NOT qualify (return stories: [] instead of forcing weak picks!):
- Pure theological commentary, lists of virtues, or standard Gospel retellings with no distinctive
  narrative hook/anecdote.
- One-sentence throwaway remarks or generic quotes without a story arc.

Be selective and strict with scores:
- 9-10: Goosebumps-level true story with unforgettable spoken line & cinematic arc (rare — top ~5% of corpus).
- 7-8: Strong, moving, clearly filmable story.
- 5-6: Decent anecdote, somewhat brief or less visual.
- <=4: Do not include.

Copy teaser_line, opening_anchor, and closing_anchor VERBATIM from the provided text."""


def prompt_hash(text):
    h = hashlib.sha256()
    h.update(f"{MODEL_NAME}|{PROMPT_VERSION}\n".encode("utf-8"))
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def compute_overall_score(scores_dict):
    # Weighted toward emotional punch + visualizability + universal appeal
    return round(
        0.35 * scores_dict["emotional_punch"]
        + 0.25 * scores_dict["visualizability"]
        + 0.25 * scores_dict["universal_appeal"]
        + 0.15 * scores_dict["standalone_clarity"],
        2,
    )


def _parse_retry_delay(exc):
    msg = str(exc)
    m = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", msg)
    if m:
        return float(m.group(1))
    return None


def extract_stories_for_meditation(client, med, max_retries=6):
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=med["embed_text"],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    response_mime_type="application/json",
                    response_schema=MeditationExtraction,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            raw = resp.text or "{}"
            parsed = MeditationExtraction.model_validate_json(raw)
            return [s.model_dump() for s in parsed.stories]
        except Exception as exc:
            if attempt == max_retries:
                raise
            suggested = _parse_retry_delay(exc)
            wait = min(suggested + 1.0, 45.0) if suggested is not None else delay
            delay = min(delay * 2.0, 30.0)
            time.sleep(wait)


def load_cache(path):
    if not os.path.exists(path):
        return {"model": MODEL_NAME, "prompt_version": PROMPT_VERSION, "entries": {}}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("model") != MODEL_NAME or data.get("prompt_version") != PROMPT_VERSION:
        return {"model": MODEL_NAME, "prompt_version": PROMPT_VERSION, "entries": {}}
    return data


def build_ranked_candidates(meditations, entries):
    by_slug = {m["slug"]: m for m in meditations}
    candidates = []
    for slug, rec in entries.items():
        if slug not in by_slug:
            continue
        med = by_slug[slug]
        for s in rec.get("stories", []):
            overall = compute_overall_score(s["scores"])
            # Bonus +0.25 for first-person true stories (Fr. Conor's own voice telling his own story!)
            bonus = 0.25 if s.get("category") == "first_person_true_story" else 0.0
            rank_score = round(overall + bonus, 2)
            candidates.append(
                {
                    "rank_score": rank_score,
                    "overall_score": overall,
                    "slug": slug,
                    "meditation_title": med["title"],
                    "url": f"{SITE_BASE}/{slug}/",
                    **s,
                }
            )
    candidates.sort(
        key=lambda c: (
            -c["rank_score"],
            -c["scores"]["emotional_punch"],
            -c["scores"]["visualizability"],
            c["slug"],
        )
    )
    for idx, c in enumerate(candidates, 1):
        c["rank"] = idx
    return candidates


_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "their", "they",
    "have", "were", "when", "what", "about", "after", "before", "where", "which",
    "story", "true", "man", "woman", "young", "life", "his", "her", "him", "she",
}


def _story_tokens(c):
    blob = f"{c['story_title']} {c['teaser_line']} {c['summary']}".lower()
    return {w for w in re.findall(r"[a-z]{4,}", blob) if w not in _STOP}


def deduplicate_candidates(candidates):
    """Group retellings of the same anecdote (e.g., Dublin Doctor told in 6 talks)
    so the Top 30 shortlist shows 30 distinct stories while preserving every source
    meditation slug where that story is told (handy for picking the best MP3)."""
    unique = []
    unique_tokens = []
    for c in candidates:
        toks = _story_tokens(c)
        matched_idx = None
        for idx, utoks in enumerate(unique_tokens):
            if not toks or not utoks:
                continue
            overlap = len(toks & utoks) / min(len(toks), len(utoks))
            if overlap >= 0.42:
                matched_idx = idx
                break
        if matched_idx is not None:
            parent = unique[matched_idx]
            also = parent.setdefault("also_told_in", [])
            if c["slug"] != parent["slug"] and all(a["slug"] != c["slug"] for a in also):
                also.append({"slug": c["slug"], "title": c["meditation_title"], "url": c["url"]})
        else:
            item = dict(c)
            item["also_told_in"] = []
            unique.append(item)
            unique_tokens.append(toks)

    for idx, c in enumerate(unique, 1):
        c["unique_rank"] = idx
    return unique


def render_top_markdown(candidates, total_meditations, top_n=30):
    unique = deduplicate_candidates(candidates)
    lines = [
        f"# Top {top_n} Unique YouTube Short-Film Story Candidates (Mined from {total_meditations} Meditations)",
        "",
        f"Generated with `{MODEL_NAME}` · Total story occurrences: **{len(candidates)}** → **{len(unique)}** unique stories across **{total_meditations}** meditations.",
        "",
        "Calibrated to the benchmark of **\"Doctor, Don't Let Me Die\"** (*The End of Life*): concrete setting, unforgettable verbatim hook, high visualizability, and universal human appeal. Retellings across multiple meditations are grouped together so you can pick the cleanest MP3 recording.",
        "",
        "## Quick-Scan Shortlist (Deduplicated)",
        "",
        "| # | Score | Story | Category | Best Source (+ Retellings) | Teaser Hook |",
        "|---:|---:|---|---|---|---|",
    ]
    for c in unique[:top_n]:
        hook = c["teaser_line"].replace("|", "\\|").replace("\n", " ")
        if len(hook) > 90:
            hook = hook[:87] + "..."
        cat = c["category"].replace("_", " ")
        extra = f" *(+{len(c['also_told_in'])} more)*" if c["also_told_in"] else ""
        lines.append(
            f"| {c['unique_rank']} | **{c['rank_score']:.2f}** | {c['story_title']} | {cat} | "
            f"[{c['meditation_title']}]({c['url']}){extra} | *\"{hook}\"* |"
        )

    lines.extend(["", "---", "", "## Detailed Production Breakdowns", ""])
    for c in unique[:top_n]:
        sc = c["scores"]
        lines.extend([
            f"### {c['unique_rank']}. {c['story_title']} — Score {c['rank_score']:.2f}",
            f"- **YouTube Title Idea:** `{c['youtube_title_idea']}`",
            f"- **Primary Source:** [{c['meditation_title']}]({c['url']}) (`{c['slug']}`)",
        ])
        if c["also_told_in"]:
            others = ", ".join(f"[{a['title']}]({a['url']})" for a in c["also_told_in"])
            lines.append(f"- **Also Told In ({len(c['also_told_in'])}):** {others}")
        lines.extend([
            f"- **Category / Setting:** `{c['category']}` · {c['era_and_setting']} (~{c['approx_word_count']} words)",
            f"- **Scores:** Emotional `{sc['emotional_punch']}` · Visual `{sc['visualizability']}` · Universal `{sc['universal_appeal']}` · Standalone `{sc['standalone_clarity']}`",
            f"- **Cold-Open Teaser Line:** *\"{c['teaser_line']}\"*",
            f"- **Story Arc:** {c['summary']}",
            f"- **Transcript Anchors:** Starts `{c['opening_anchor']}` → Ends `{c['closing_anchor']}`",
            "- **Visual Beats:**",
        ])
        for beat in c.get("visual_beats", []):
            lines.append(f"  - {beat}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Mine meditations for YouTube short-film stories.")
    parser.add_argument("--force", "-f", action="store_true", help="Rescan all meditations")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent API workers (default: 8)")
    parser.add_argument("--limit", type=int, default=0, help="Limit uncached items processed (0 = all)")
    parser.add_argument("--top-n", type=int, default=30, help="Entries in Markdown shortlist")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(os.path.dirname(script_dir), "transcript_proofread_std_markdown")
    data_dir = os.path.join(script_dir, "data")
    cache_path = os.path.join(data_dir, "film_stories_cache.json")
    out_json = os.path.join(data_dir, "film_candidates.json")
    out_md = os.path.join(data_dir, "TOP_30_FILM_STORIES.md")

    meditations = load_corpus(source_dir, data_dir)
    for m in meditations:
        m["scan_sha"] = prompt_hash(m["embed_text"])

    cache = load_cache(cache_path)
    entries = {} if args.force else dict(cache.get("entries", {}))

    active_slugs = {m["slug"] for m in meditations}
    for s in [k for k in entries if k not in active_slugs]:
        del entries[s]

    to_scan = [
        m for m in meditations
        if m["slug"] not in entries or entries[m["slug"]].get("sha256") != m["scan_sha"]
    ]
    if args.limit > 0:
        to_scan = to_scan[: args.limit]

    print(
        f"Story Miner ({MODEL_NAME}): {len(meditations)} meditations, "
        f"{len(meditations) - len(to_scan)} cached, {len(to_scan)} to scan (workers={args.workers}).",
        flush=True,
    )

    if to_scan:
        api_key = resolve_api_key(script_dir)
        if not api_key:
            print("ERROR: GEMINI_API_KEY not found.", file=sys.stderr)
            sys.exit(1)

        client = genai.Client(api_key=api_key)
        lock = threading.Lock()
        t0 = time.time()
        total = len(to_scan)
        already = len(entries)
        done = 0
        errors = 0

        def worker(med):
            stories = extract_stories_for_meditation(client, med)
            return med["slug"], med["scan_sha"], stories

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(worker, m): m for m in to_scan}
            for fut in as_completed(futs):
                med = futs[fut]
                try:
                    slug, sha, stories = fut.result()
                    with lock:
                        entries[slug] = {"sha256": sha, "stories": stories}
                        done += 1
                        if done % 20 == 0 or done == total:
                            save_json_atomic(
                                cache_path,
                                {
                                    "model": MODEL_NAME,
                                    "prompt_version": PROMPT_VERSION,
                                    "entries": entries,
                                },
                                compact=True,
                            )
                            elapsed = time.time() - t0
                            rate = done / elapsed if elapsed > 0 else 0
                            eta = (total - done) / rate if rate > 0 else 0
                            pct = 100.0 * len(entries) / len(meditations)
                            print(
                                f"  Scanned {len(entries)}/{len(meditations)} ({pct:.1f}%) "
                                f"[{elapsed:.0f}s elapsed, ~{eta:.0f}s left, errors={errors}]",
                                flush=True,
                            )
                except Exception as exc:
                    with lock:
                        errors += 1
                        print(
                            f"  ERROR on {med['slug']}: {type(exc).__name__}: {exc}",
                            file=sys.stderr,
                            flush=True,
                        )

        save_json_atomic(
            cache_path,
            {"model": MODEL_NAME, "prompt_version": PROMPT_VERSION, "entries": entries},
            compact=True,
        )

    candidates = build_ranked_candidates(meditations, entries)
    save_json_atomic(
        out_json,
        {
            "model": MODEL_NAME,
            "prompt_version": PROMPT_VERSION,
            "meditations_scanned": len(entries),
            "total_candidates": len(candidates),
            "candidates": candidates,
        },
        compact=False,
    )
    md_text = render_top_markdown(candidates, len(meditations), top_n=args.top_n)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(
        f"Done! Extracted {len(candidates)} story candidates across {len(entries)} meditations.",
        flush=True,
    )
    print(f"  JSON: {out_json}", flush=True)
    print(f"  Shortlist: {out_md}", flush=True)


if __name__ == "__main__":
    main()
