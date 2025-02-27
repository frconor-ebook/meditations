#!/bin/bash

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown"

# Ensure the destination directory exists
mkdir -p "$dest_dir"

# Count total .doc/.docx files in the source directory
total=$(find "$source_dir" -name "*.doc*" | wc -l)
echo "Found $total files to process."

# Initialize a counter (note: this counter is updated in the subshell below)
count=0

# Find files using -print0 for safety; convert nulls to newlines for pv's -l mode.
# pv will show progress as it counts the lines (files) processed.
find "$source_dir" -name "*.doc*" -print0 | tr '\0' '\n' | pv -l -s "$total" | while IFS= read -r doc_file; do
  # Increment the counter
  ((count++))
  echo "Processing file #$count: $doc_file"

  # Generate the corresponding output Markdown filename
  markdown_file="$dest_dir/$(basename "$doc_file" | sed 's/\.doc[x]*$/.md/')"

  # Convert the file (assuming convert.sh handles the conversion)
  ./convert_fast.sh "$doc_file" > "$markdown_file"
  # ./convert.sh "$doc_file" > "$markdown_file"

  # Check if the conversion was successful and provide feedback
  if [ $? -eq 0 ]; then
    echo "Successfully converted '$doc_file' to '$markdown_file'"
  else
    echo "Error converting '$doc_file' to '$markdown_file'"
  fi
done

# Note: Because the while loop is in a pipe, $count here will not reflect the updated value.
# If you need to use $count outside, consider using process substitution to avoid a subshell.