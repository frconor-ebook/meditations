import json
import os
import re
import shutil
import unicodedata  # Add this import
from datetime import datetime


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


def convert_markdown_to_posts(source_dir, posts_dir, data_dir):
    """
    Converts markdown files to Jekyll posts and creates a meditations.json index.
    """

    meditations = []
    for filename in os.listdir(source_dir):
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

            with open(post_filepath, "w") as f:
                f.write(front_matter)
                f.writelines(
                    [
                        line.rstrip("\r\n") + "\n"
                        for line in lines[title_line_index + 1 :]
                    ]
                )

            # Get full content
            full_content = "".join(
                [line.rstrip("\r\n") for line in lines[title_line_index + 1 :]]
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
    source_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_std_markdown"
    posts_directory = (
        "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/_posts"
    )
    data_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/data"

    if os.path.exists(posts_directory):
        shutil.rmtree(posts_directory)
        print(f"Removed existing directory: {posts_directory}")

    os.makedirs(posts_directory, exist_ok=True)

    print(f"Source Directory: {source_directory}")
    print(f"Posts Directory: {posts_directory}")
    print(f"Data Directory: {data_directory}")

    convert_markdown_to_posts(source_directory, posts_directory, data_directory)
