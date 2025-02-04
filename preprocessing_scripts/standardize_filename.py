import os
import re
import shutil
import sys


def standardize_filenames(source_dir, output_dir):
    """
    Standardizes filenames in the given directory and copies them to a new directory.

    Steps:
    1. Converts filenames to lowercase.
    2. Replaces spaces and special characters with hyphens and removes non-ASCII characters.
    3. Keeps only lowercase letters, numbers, hyphens, and dots.
    4. Removes duplicate hyphens.
    5. Truncates filenames that exceed 250 characters (excluding the ".md" extension).
    6. Copies the standardized files to the output directory.
    """

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Iterate through all files in the source directory
    for filename in os.listdir(source_dir):
        filepath = os.path.join(source_dir, filename)

        # Process only Markdown (.md) files
        if filename.endswith(".md"):
            # 1. Convert filename to lowercase
            new_filename = filename.lower()

            # 2. Remove non-ASCII characters
            new_filename = re.sub(r"[^\x00-\x7F]+", "", new_filename)

            # 3. Replace spaces and slashes with hyphens
            new_filename = re.sub(r"[ /]+", "-", new_filename)

            # 4. Keep only lowercase letters, numbers, hyphens, and dots
            new_filename = re.sub(r"[^a-z0-9-.]", "", new_filename)

            # 5. Remove duplicate hyphens
            new_filename = re.sub(r"[-]+", "-", new_filename)

            # 6. Truncate filename if it exceeds 250 characters (keeping the extension)
            max_length = 250  # Maximum length excluding extension
            if len(new_filename) > max_length + 3:  # +3 accounts for ".md"
                root, ext = os.path.splitext(new_filename)

                # If extension is too long, enforce ".md" and truncate everything else
                if len(ext) >= max_length:
                    ext = ".md"
                    root = ""
                else:
                    root = root[: (max_length - len(ext))]

                new_filename = root + ext

            # Construct new file path in the output directory
            new_filepath = os.path.join(output_dir, new_filename)

            # Copy the file with the new standardized name
            shutil.copy2(filepath, new_filepath)
            print(f"Copied and renamed '{filename}' to '{new_filepath}'")

        else:
            print(f"Skipping non-.md file: '{filename}'")


if __name__ == "__main__":
    # Define source and output directories
    source_directory = "transcript_proofread_markdown"  # Directory containing the original Markdown files
    output_directory = (
        "transcript_proofread_std_markdown"  # Directory for standardized filenames
    )

    # Check if the source directory exists
    if not os.path.isdir(source_directory):
        print(f"Error: '{source_directory}' is not a valid directory.")
        sys.exit(1)

    # Run the filename standardization function
    standardize_filenames(source_directory, output_directory)
    print("Finished standardizing filenames.")
