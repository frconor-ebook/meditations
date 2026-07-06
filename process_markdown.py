import argparse
import os
import re
import json
import shutil
import unicodedata


def sanitize_title(title):
    """
    Sanitize title by removing Word-style superscript notation.
    Converts patterns like 2^(nd), 10^(th), 26^(th) to 2nd, 10th, 26th
    """
    # Replace common ordinal superscripts
    title = re.sub(r'(\d+)\^\(st\)', r'\1st', title)  # 1^(st) -> 1st
    title = re.sub(r'(\d+)\^\(nd\)', r'\1nd', title)  # 2^(nd) -> 2nd
    title = re.sub(r'(\d+)\^\(rd\)', r'\1rd', title)  # 3^(rd) -> 3rd
    title = re.sub(r'(\d+)\^\(th\)', r'\1th', title)  # 4^(th) -> 4th

    return title


def make_slug(title):
    """Create a URL slug from a title (lowercase, no diacritics, hyphenated)."""
    slug = title.lower()
    slug = unicodedata.normalize("NFKD", slug)
    slug = re.sub(r"[\u0300-\u036f]", "", slug)  # Remove combining diacritics
    slug = re.sub(r"[^\w\s-]", "", slug).replace(
        " ", "-"
    )  # Keep word chars, spaces and hyphens
    slug = re.sub(r"[-]+", "-", slug)  # Remove duplicate hyphens
    return slug.strip("-")


def remove_duplicate_title_lines(lines, title):
    """
    Remove lines that are duplicate bold versions of the title.
    Handles patterns like **Title**, *Title*, or just Title on its own line.
    """
    # Normalize title for comparison (remove punctuation, lowercase)
    def normalize(text):
        text = re.sub(r'[^\w\s]', '', text.lower())
        return ' '.join(text.split())

    normalized_title = normalize(title)
    filtered_lines = []

    for line in lines:
        stripped = line.strip()

        # Check for bold title: **Title** or __Title__
        bold_match = re.match(r'^(\*\*|__)(.+?)(\*\*|__)$', stripped)
        if bold_match:
            potential_title = bold_match.group(2).strip()
            if normalize(potential_title) == normalized_title:
                continue  # Skip this duplicate title line

        # Check for italic title that matches exactly: *Title*
        italic_match = re.match(r'^\*([^*]+)\*$', stripped)
        if italic_match:
            potential_title = italic_match.group(1).strip()
            if normalize(potential_title) == normalized_title:
                continue  # Skip this duplicate title line

        # Check for plain text title (no formatting) that matches exactly
        if stripped and normalize(stripped) == normalized_title:
            continue  # Skip this duplicate title line

        filtered_lines.append(line)

    return filtered_lines


def make_excerpt(content_lines, max_words=400):
    """
    Build the search/display excerpt for a meditation.

    Skips the standard opening boilerplate every meditation shares (byline,
    proofread marker, italic opening prayers) so excerpts start at the real
    content, strips emphasis markers for clean snippets, and truncates.
    """
    def is_boilerplate(paragraph):
        if paragraph.lower().startswith("by fr"):
            return True
        if paragraph.strip("*() ").lower() == "proofread":
            return True
        # Fully-italicized paragraph at the head = opening prayer
        if paragraph.startswith("*") and paragraph.endswith("*"):
            return True
        return False

    paragraphs = [line.strip() for line in content_lines if line.strip()]
    body = []
    skipping = True
    for paragraph in paragraphs:
        if skipping and is_boilerplate(paragraph):
            continue
        skipping = False
        body.append(paragraph)

    text = re.sub(r"[*_]+", "", " ".join(body))
    words = text.split()
    excerpt = " ".join(words[:max_words])
    if len(words) > max_words:
        excerpt += "..."
    return excerpt


def make_description(excerpt, max_chars=155):
    """Meta description: excerpt truncated to ~max_chars on a word boundary."""
    if len(excerpt) <= max_chars:
        return excerpt
    cut = excerpt.rfind(" ", 0, max_chars)
    if cut == -1:
        cut = max_chars
    return excerpt[:cut].rstrip(".,;:") + "..."


def convert_markdown_to_meditations(source_dir, output_dir, data_dir):
    """
    Converts all source markdown files to Jekyll collection documents in
    _meditations/ and (re)creates the JSON indexes.

    This is a full rebuild on every run: filenames are slug-based (no dates),
    so output is deterministic — unchanged sources produce byte-identical
    files, and deletions/renames in the source folder sync automatically.
    """
    # Start clean so removed/renamed sources disappear from the site
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    meditations = []
    slug_sources = {}

    for filename in sorted(os.listdir(source_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(source_dir, filename)

        with open(filepath, "r") as f:
            lines = f.readlines()

        title_line_index = -1
        for i, line in enumerate(lines):
            if line.rstrip("\r\n").lstrip().startswith("#"):
                title_line_index = i
                break

        if title_line_index == -1:
            print(f"Skipping {filename} (no title found).")
            continue

        title = lines[title_line_index].rstrip("\r\n").lstrip("# ").strip()
        title = sanitize_title(title)  # Sanitize Word-style superscripts

        slug = make_slug(title)
        if not slug:
            print(
                f"Skipping {filename}: heading '{title}' produced an empty slug. "
                f"Fix the source file's first '#' heading."
            )
            continue

        if slug in slug_sources:
            # Two source files produce the same slug (e.g. a stray copy in
            # Dropbox). Keep the later one (sorted order) so the choice is
            # deterministic, and warn so the stray can be cleaned up.
            print(
                f"WARNING: duplicate slug '{slug}': {filename} replaces "
                f"{slug_sources[slug]}. Remove the stray copy from Dropbox."
            )
            meditations = [m for m in meditations if m["slug"] != slug]
        slug_sources[slug] = filename

        # Get content lines (after the title) and clean up
        content_lines = lines[title_line_index + 1 :]
        content_lines = remove_duplicate_title_lines(content_lines, title)

        excerpt = make_excerpt(content_lines)

        # json.dumps produces valid YAML double-quoted strings, so titles or
        # descriptions containing quotes cannot break the front matter
        front_matter = (
            "---\n"
            "layout: homily\n"
            f"title: {json.dumps(title)}\n"
            f"description: {json.dumps(make_description(excerpt))}\n"
            "---\n"
        )

        with open(os.path.join(output_dir, f"{slug}.md"), "w") as f:
            f.write(front_matter)
            f.writelines(
                [
                    line.rstrip("\r\n") + "\n"
                    for line in content_lines
                ]
            )

        # Get full content (join lines with spaces, collapse whitespace)
        full_content = " ".join(
            "\n".join(line.rstrip("\r\n") for line in content_lines).split()
        )

        meditations.append(
            {
                "title": title,
                "slug": slug,
                "content": full_content,
                "excerpt": excerpt,
            }
        )

    meditations.sort(key=lambda x: x["title"])

    os.makedirs(data_dir, exist_ok=True)

    # Full index: local artifact only (gitignored), used by the URL-shortener
    meditations_json_path = os.path.join(data_dir, "meditations.json")
    with open(meditations_json_path, "w") as f:
        json.dump(meditations, f, indent=2)
    print(f"Created: {meditations_json_path}")

    # Lightweight search index (title, slug, excerpt only), shipped to visitors
    search_index = [
        {"title": m["title"], "slug": m["slug"], "excerpt": m["excerpt"]}
        for m in meditations
    ]
    search_index_path = os.path.join(data_dir, "search_index.json")
    with open(search_index_path, "w") as f:
        # Minified: this file is shipped to every visitor who searches
        json.dump(search_index, f, separators=(",", ":"))
    print(f"Created: {search_index_path}")

    print(f"Processed {len(meditations)} meditations.")


# --- Main execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process source markdown files into the Jekyll meditations collection."
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="No-op, kept for pipeline compatibility (processing always rebuilds fully)"
    )
    parser.parse_args()

    # Get the directory where this script is located (meditations/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Parent directory is upload_frcmed_to_web (one level up from meditations)
    parent_dir = os.path.dirname(script_dir)

    source_directory = os.path.join(parent_dir, "transcript_proofread_std_markdown")
    output_directory = os.path.join(script_dir, "_meditations")
    data_directory = os.path.join(script_dir, "data")

    print(f"Source Directory: {source_directory}")
    print(f"Output Directory: {output_directory}")
    print(f"Data Directory: {data_directory}")

    convert_markdown_to_meditations(
        source_directory, output_directory, data_directory
    )
