#!/bin/bash

# Set the source and destination directories
source_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_MSWord"
dest_dir="/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/transcript_proofread_markdown"

# Ensure the destination directory exists
mkdir -p "$dest_dir"

# Count total .doc/.docx files in the source directory.  Use -regex for case-insensitivity.
total=$(find "$source_dir" -iregex '.*\.\(doc\|docx\)' | wc -l)
echo "Found $total files to process."

# Find files using -print0 for safety and use GNU parallel for processing.
find "$source_dir" -iregex '.*\.\(doc\|docx\)' -print0 |
  parallel -0 -j $(nproc) --bar --eta \
    # './convert_fast.sh "{}" > "'"$dest_dir"'/$(basename "{}" | sed "s/\.doc[x]*$/.md/")"'
    './convert.sh "{}" > "'"$dest_dir"'/$(basename "{}" | sed "s/\.doc[x]*$/.md/")"'

echo "Conversion complete."