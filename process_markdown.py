import json
import os
import re
import shutil
from datetime import datetime


def convert_markdown_to_posts(source_dir, posts_dir, data_dir):
    """
    Converts markdown files to Jekyll posts and creates a meditations.json index.

    Args:
        source_dir: Directory containing the source markdown files.
        posts_dir: Directory where Jekyll post files will be created.
        data_dir: Directory where meditations.json will be created.
    """

    meditations = []
    for filename in os.listdir(source_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(source_dir, filename)
            print(f"Processing: {filename}")

            with open(filepath, "r") as f:
                lines = f.readlines()

            # Find the first line that starts with "#" (title line)
            title_line_index = -1
            for i, line in enumerate(lines):
                # Strip any trailing \r or \n and check for "#" at the start
                if line.rstrip("\r\n").lstrip().startswith("#"):
                    title_line_index = i
                    break

            # Skip files without a title line
            if title_line_index == -1:
                print(f"Skipping {filename} (no title found).")
                continue

            # Extract title from the title line
            # Strip any trailing \r or \n and remove "#" and spaces
            title = lines[title_line_index].rstrip("\r\n").lstrip("# ").strip()

            # Create a slug for the URL
            slug = re.sub(r"[^\w\s-]", "", title).lower().replace(" ", "-")

            # Generate post filename with current date
            post_filename = f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
            print(post_filename)
            post_filepath = os.path.join(posts_dir, post_filename)

            # Create YAML front matter
            front_matter = f"""---
layout: homily
title: "{title}"
---
"""

            # Write the post file (skip lines before title and the title line itself)
            with open(post_filepath, "w") as f:
                f.write(front_matter)
                # Remove trailing \r from each line before writing
                f.writelines(
                    [
                        line.rstrip("\r\n") + "\n"
                        for line in lines[title_line_index + 1 :]
                    ]
                )

            # Add to meditations list for JSON index
            meditations.append(
                {
                    "title": title,
                    "slug": slug,
                    "content": "".join(
                        [line.rstrip("\r\n") for line in lines[title_line_index + 1 :]]
                    ).strip(),
                }
            )

    # Create meditations.json
    meditations_json_path = os.path.join(data_dir, "meditations.json")
    print(f"meditations_json_path: {meditations_json_path}")

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(meditations_json_path), exist_ok=True)
    print(
        f"Directory created (or already exists): {os.path.dirname(meditations_json_path)}"
    )

    meditations.sort(key=lambda x: x["title"])  # Add this line
    try:
        with open(meditations_json_path, "w") as f:
            json.dump(meditations, f, indent=2)
            print(
                f"Successfully created: {meditations_json_path}"
            )  # Print success message
    except Exception as e:
        print(f"Error creating {meditations_json_path}: {e}")  # Print error message

    print(f"Processed {len(meditations)} markdown files.")


# --- Main execution ---
if __name__ == "__main__":
    source_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_std_markdown"  # Change to your source directory
    posts_directory = (
        "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/_posts"
    )
    data_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/data"  # Output directory for meditations.json

    # Remove the existing _posts directory if it exists
    if os.path.exists(posts_directory):
        shutil.rmtree(posts_directory)
        print(f"Removed existing directory: {posts_directory}")

    # Create the _posts directory (it will be created empty)
    os.makedirs(posts_directory, exist_ok=True)

    print(f"Source Directory: {source_directory}")
    print(f"Posts Directory: {posts_directory}")
    print(f"Data Directory: {data_directory}")

    convert_markdown_to_posts(source_directory, posts_directory, data_directory)
