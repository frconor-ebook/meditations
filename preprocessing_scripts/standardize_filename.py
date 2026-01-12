import os
import re
import shutil
import sys
import unicodedata


def standardize_filenames(source_dir, output_dir):
    """Standardizes filenames."""
    if os.path.exists(output_dir):
        print(f"Removing existing output directory: '{output_dir}'")
        shutil.rmtree(output_dir)
    print(f"Creating new output directory: '{output_dir}'")
    os.makedirs(output_dir)
    for filename in os.listdir(source_dir):
        filepath = os.path.join(source_dir, filename)
        if filename.endswith(".md"):
            new_filename = filename.lower()
            new_filename = unicodedata.normalize("NFKD", new_filename)
            new_filename = re.sub(r"[\u0300-\u036f]", "", new_filename)
            new_filename = re.sub(r"[ /]+", "-", new_filename)
            new_filename = re.sub(r"[^a-z0-9-.]", "", new_filename)
            new_filename = re.sub(r"[-]+", "-", new_filename)
            max_length = 250
            if len(new_filename) > max_length + 3:
                root, ext = os.path.splitext(new_filename)
                if len(ext) >= max_length:
                    ext = ".md"
                    root = ""
                else:
                    root = root[: (max_length - len(ext))]
                new_filename = root + ext
            new_filepath = os.path.join(output_dir, new_filename)
            shutil.copy2(filepath, new_filepath)
            print(f"Copied and renamed '{filename}' to '{new_filename}'")
        else:
            print(f"Skipping non-.md file: '{filename}'")


if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Parent directory is upload_frcmed_to_web (two levels up: preprocessing_scripts -> meditations -> upload_frcmed_to_web)
    parent_dir = os.path.dirname(os.path.dirname(script_dir))

    source_directory = os.path.join(parent_dir, "transcript_proofread_markdown")
    output_directory = os.path.join(parent_dir, "transcript_proofread_std_markdown")

    if not os.path.isdir(source_directory):
        print(f"Error: '{source_directory}' is not a valid directory.")
        sys.exit(1)
    standardize_filenames(source_directory, output_directory)
    print("Finished standardizing filenames.")
