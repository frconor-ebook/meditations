import os
import re
import sys
import shutil

def standardize_filenames(source_dir, output_dir):
    """
    Standardizes filenames and saves them to a new directory.
    """
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(source_dir):
        filepath = os.path.join(source_dir, filename)
        if filename.endswith(".md"):
            # 1. Convert to lowercase
            new_filename = filename.lower()

            # 2. Replace spaces and special characters with hyphens, remove non-ASCII
            new_filename = re.sub(r"[^\x00-\x7F]+", "", new_filename)  # Remove non-ASCII
            new_filename = re.sub(r"[ /]+", "-", new_filename)  # Spaces and slashes to -
            new_filename = re.sub(
                r"[^a-z0-9-.]", "", new_filename
            )  # Keep only lowercase, numbers, hyphens, dots

            # 3. Remove duplicate hyphens
            new_filename = re.sub(r"[-]+", "-", new_filename)

            # 4. Truncate filename if too long (keep extension)
            max_length = 250  # Max length excluding extension
            if len(new_filename) > max_length + 3:  # +3 to account for ".md"
                root, ext = os.path.splitext(new_filename)
                if len(ext) >= max_length:
                    ext = ".md"
                    root = ""
                else:
                    root = root[: (max_length - len(ext))]
                new_filename = root + ext

            # Construct new_filepath using output_dir
            new_filepath = os.path.join(output_dir, new_filename)

            # Copy the file
            shutil.copy2(filepath, new_filepath)
            print(f"Copied and renamed '{filename}' to '{new_filepath}'")
        else:
            print(f"Skipping non-.md file: '{filename}'")

if __name__ == "__main__":

    source_directory = "transcript_proofread_markdown"
    output_directory = "transcript_proofread_std_markdown"

    if not os.path.isdir(source_directory):
        print(f"Error: '{source_directory}' is not a valid directory.")
        sys.exit(1)

    standardize_filenames(source_directory, output_directory)
    print("Finished standardizing filenames.")