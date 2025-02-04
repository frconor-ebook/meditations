#!/bin/bash

# Wrapper script for 'convert.sh'
# - This script finds all .doc and .docx files in a source directory
# - Calls 'convert.sh' to convert each file to Markdown
# - Saves the converted files in a specified destination directory

# Set the source directory containing proofread transcripts in MS Word format
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web_base/transcript_proofread_MSWord"

# Set the destination directory for the converted Markdown files
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web_base/transcript_proofread_markdown"

# Ensure the destination directory exists, creating it if necessary
mkdir -p "$dest_dir"

# Find all .doc and .docx files in the source directory and process them
find "$source_dir" -name "*.doc*" -print0 | while IFS= read -r -d $'\0' doc_file; do
  # Generate the corresponding output Markdown filename
  markdown_file="$dest_dir/$(basename "$doc_file" | sed 's/\.doc[x]*$/.md/')"

  # Use 'convert.sh' to perform the actual conversion, saving the output to the Markdown file
  ./convert.sh "$doc_file" > "$markdown_file"

  # Check if the conversion was successful and provide feedback
  if [ $? -eq 0 ]; then
    echo "Successfully converted '$doc_file' to '$markdown_file'"
  else
    echo "Error converting '$doc_file' to '$markdown_file'"
  fi
done
