import argparse
import json
import os
import re
import shutil
import unicodedata
from datetime import datetime

from file_manifest import (
    compute_file_hash,
    get_changed_files,
    load_manifest,
    save_manifest,
)


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

        filtered_lines.append(line)

    return filtered_lines


def remove_proofread_markers(lines):
    """
    Remove lines that contain proofreader markers like (Proofread), (*Proofread*), etc.
    These are internal markers that shouldn't appear in the final content.
    Handles variants: (Proofread), (*Proofread*), (*Proofread)*, etc.
    """
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that contain "Proofread" as a standalone marker
        # This catches: (Proofread), (*Proofread*), (*Proofread)*, *Proofread*, etc.
        if re.match(r'^[\s\(\)\*]*Proofread[\s\(\)\*]*$', stripped, re.IGNORECASE):
            continue
        filtered_lines.append(line)
    return filtered_lines


def convert_markdown_to_posts(source_dir, posts_dir, data_dir, force=False):
    """
    Converts markdown files to Jekyll posts and creates a meditations.json index.

    Args:
        source_dir: Directory containing source markdown files
        posts_dir: Directory for Jekyll posts
        data_dir: Directory for JSON data files
        force: If True, process all files regardless of changes
    """
    # Get the script directory for manifest
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load manifest and check for changes
    manifest = load_manifest(script_dir)

    if force:
        print("Force mode: Processing all files...")
        files_to_process = [f for f in os.listdir(source_dir) if f.endswith(".md")]
        files_to_delete = []
        # Compute hashes for all files
        current_hashes = {}
        for filename in files_to_process:
            filepath = os.path.join(source_dir, filename)
            file_hash = compute_file_hash(filepath)
            if file_hash:
                current_hashes[filename] = file_hash
    else:
        print("Checking for changed markdown files...")
        files_to_process, files_to_delete, current_hashes = get_changed_files(
            source_dir, "markdown_hashes", manifest
        )

        if not files_to_process and not files_to_delete:
            print("No markdown files have changed. Skipping processing.")
            return

        print(f"  Files to process: {len(files_to_process)}")
        print(f"  Files to delete: {len(files_to_delete)}")

    # Handle deleted files - remove their corresponding posts
    for filename in files_to_delete:
        # Find and remove the post file
        base_name = os.path.splitext(filename)[0]
        for post_file in os.listdir(posts_dir) if os.path.exists(posts_dir) else []:
            if post_file.endswith(f"-{base_name}.md") or base_name in post_file:
                post_path = os.path.join(posts_dir, post_file)
                print(f"Removing deleted post: {post_file}")
                os.remove(post_path)

    # Ensure posts directory exists
    os.makedirs(posts_dir, exist_ok=True)

    # Load existing meditations from JSON if doing incremental update
    existing_meditations = {}
    meditations_json_path = os.path.join(data_dir, "meditations.json")
    if not force and os.path.exists(meditations_json_path):
        try:
            with open(meditations_json_path, "r") as f:
                for m in json.load(f):
                    existing_meditations[m.get("slug")] = m
        except (json.JSONDecodeError, IOError):
            pass

    meditations = []
    processed_slugs = set()

    # Process changed/new files
    for filename in files_to_process:
        if filename.endswith(".md"):
            filepath = os.path.join(source_dir, filename)
            print(f"Processing: {filename}")

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

            # Create a slug for the URL (MODIFIED FOR CONSISTENCY)
            slug = title.lower()
            slug = unicodedata.normalize("NFKD", slug)
            slug = re.sub(r"[\u0300-\u036f]", "", slug)  # Remove combining diacritics
            slug = re.sub(r"[^\w\s-]", "", slug).replace(
                " ", "-"
            )  # Keep word chars, spaces and hyphens
            slug = re.sub(r"[-]+", "-", slug)  # Remove duplicate hyphens

            post_filename = f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
            print(post_filename)
            post_filepath = os.path.join(posts_dir, post_filename)

            front_matter = f"""---
layout: homily
title: "{title}"
---
"""

            # Get content lines (after the title) and clean up
            content_lines = lines[title_line_index + 1 :]
            content_lines = remove_duplicate_title_lines(content_lines, title)
            content_lines = remove_proofread_markers(content_lines)

            with open(post_filepath, "w") as f:
                f.write(front_matter)
                f.writelines(
                    [
                        line.rstrip("\r\n") + "\n"
                        for line in content_lines
                    ]
                )

            # Get full content
            full_content = "".join(
                [line.rstrip("\r\n") for line in content_lines]
            ).strip()

            # Create excerpt (first 200 words of content)
            words = full_content.split()
            if len(words) > 200:
                excerpt = " ".join(words[:200]) + "..."
            else:
                excerpt = full_content

            meditations.append(
                {
                    "title": title,
                    "slug": slug,
                    "content": full_content,
                    "excerpt": excerpt,
                }
            )
            processed_slugs.add(slug)

    # For incremental updates, merge with existing meditations that weren't processed
    if not force and existing_meditations:
        # Remove deleted slugs from existing_meditations
        deleted_slugs = set()
        for filename in files_to_delete:
            # Try to find the slug for this file from existing meditations
            base_name = os.path.splitext(filename)[0].lower().replace(" ", "-")
            for slug in existing_meditations:
                if base_name in slug or slug in base_name:
                    deleted_slugs.add(slug)

        # Add unchanged meditations back
        for slug, meditation in existing_meditations.items():
            if slug not in processed_slugs and slug not in deleted_slugs:
                meditations.append(meditation)

    # Update manifest with new hashes
    manifest["markdown_hashes"] = current_hashes
    save_manifest(script_dir, manifest)
    print(f"Updated manifest with {len(current_hashes)} file hashes.")

    meditations_json_path = os.path.join(data_dir, "meditations.json")
    print(f"meditations_json_path: {meditations_json_path}")

    os.makedirs(os.path.dirname(meditations_json_path), exist_ok=True)
    print(
        f"Directory created (or already exists): {os.path.dirname(meditations_json_path)}"
    )

    meditations.sort(key=lambda x: x["title"])

    # Write full meditations.json (for backward compatibility)
    try:
        with open(meditations_json_path, "w") as f:
            json.dump(meditations, f, indent=2)
            print(f"Successfully created: {meditations_json_path}")
    except Exception as e:
        print(f"Error creating {meditations_json_path}: {e}")

    # Create lightweight search index (title, slug, excerpt only)
    search_index = [
        {"title": m["title"], "slug": m["slug"], "excerpt": m["excerpt"]}
        for m in meditations
    ]
    search_index_path = os.path.join(data_dir, "search_index.json")
    try:
        with open(search_index_path, "w") as f:
            json.dump(search_index, f, indent=2)
            print(f"Successfully created: {search_index_path}")

            # Report file sizes for comparison
            full_size = os.path.getsize(meditations_json_path) / (1024 * 1024)  # MB
            search_size = os.path.getsize(search_index_path) / (1024 * 1024)  # MB
            print(f"  Full index size: {full_size:.2f} MB")
            print(f"  Search index size: {search_size:.2f} MB")
            print(f"  Size reduction: {(1 - search_size/full_size) * 100:.1f}%")
    except Exception as e:
        print(f"Error creating {search_index_path}: {e}")

    print(f"Processed {len(meditations)} markdown files.")


# --- Main execution ---
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Process markdown files into Jekyll posts with incremental updates."
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force processing of all files (ignore change detection)"
    )
    args = parser.parse_args()

    # Get the directory where this script is located (meditations/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Parent directory is upload_frcmed_to_web (one level up from meditations)
    parent_dir = os.path.dirname(script_dir)

    source_directory = os.path.join(parent_dir, "transcript_proofread_std_markdown")
    posts_directory = os.path.join(script_dir, "_posts")
    data_directory = os.path.join(script_dir, "data")

    # Only delete posts directory in force mode
    if args.force and os.path.exists(posts_directory):
        shutil.rmtree(posts_directory)
        print(f"Force mode: Removed existing directory: {posts_directory}")

    os.makedirs(posts_directory, exist_ok=True)

    print(f"Source Directory: {source_directory}")
    print(f"Posts Directory: {posts_directory}")
    print(f"Data Directory: {data_directory}")

    convert_markdown_to_posts(
        source_directory, posts_directory, data_directory, force=args.force
    )
