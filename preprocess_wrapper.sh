#!/bin/bash

# Set the base directory relative to the script's location.
# This ensures the script works correctly even if moved, as long as the
# directory structure within 'upload_frcmed_to_web' remains the same.
# The script assumes it is located in 'upload_frcmed_to_web/meditations/'.
BASE_DIR="$(cd "$(dirname "$0")" && pwd)/.."

# Function to display error messages and exit the script.
#
# Arguments:
#   $1: The error message to display.
error_message() {
  echo "Error: $1" >&2  # Print the error message to standard error (>&2).
  exit 1                # Exit the script with a non-zero exit code (indicating an error).
}

# Convert DocX to Markdown.
echo "Converting DocX to Markdown..."
# Change directory to where the conversion script is located.
# If 'cd' fails (e.g., directory not found), call the error_message function.
cd "$BASE_DIR/meditations/preprocessing_scripts/" || error_message "Could not change to preprocessing_scripts directory."
# Execute the conversion script.
# If it returns a non-zero exit code (indicating an error), call error_message.
./convert_all_to_md.sh || error_message "DocX to Markdown conversion failed."

# Standardize Filenames.
echo "Standardizing filenames..."
# Execute the Python script for standardizing filenames.
# We assume it's in the same directory as convert_all_to_md.sh.
# If the script fails, call error_message.
python standardize_filename.py || error_message "Filename standardization failed."

# Process Markdown Files.
echo "Processing Markdown files..."
# Change directory to where the Markdown processing script is located.
cd "$BASE_DIR/meditations" || error_message "Could not change to meditations directory."
# Execute the Markdown processing script.
# If it fails, call error_message.
python process_markdown.py || error_message "Markdown processing failed."

# Indicate successful completion.
echo "Preprocessing steps completed successfully."