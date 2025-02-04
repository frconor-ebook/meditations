#!/bin/bash

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web_base/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web_base/transcript_proofread_markdown"

# Create the destination directory if it doesn't exist
mkdir -p "$dest_dir"

# Find all .doc and .docx files in the source directory
find "$source_dir" -name "*.doc*" -print0 | while IFS= read -r -d $'\0' doc_file; do
  # Construct the output markdown file path
  markdown_file="$dest_dir/$(basename "$doc_file" | sed 's/\.doc[x]*$/.md/')"

  # Convert the doc file to markdown using convert.sh
  ./convert.sh "$doc_file" > "$markdown_file"

  # Check if conversion was successful and display appropriate message
  if [ $? -eq 0 ]; then
    echo "Successfully converted '$doc_file' to '$markdown_file'"
  else
    echo "Error converting '$doc_file' to '$markdown_file'"
  fi
done