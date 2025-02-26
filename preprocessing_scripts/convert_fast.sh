#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_docx_file>"
    exit 1
fi

input_docx="$1"

if [ ! -f "$input_docx" ]; then
    echo "Error: File '$input_docx' not found!"
    exit 1
fi

# Extract the entire document as Markdown
body=$(pandoc -s --to=markdown "$input_docx" 2>/dev/null)

# --- Title Extraction Logic ---

# 1. Try to extract title assuming it's formatted as "# Title" (rare, but possible)
title=$(echo "$body" | sed -n 's/^# //p' | head -n 1)

# 2. If title is empty, try to get title from YAML (more common)
if [ -z "$title" ]; then
    title=$(echo "$body" | sed -n 's/^title: //p' | head -n 1)
fi

# 3. If title is *still* empty, extract the first non-blank line AFTER the YAML frontmatter
if [ -z "$title" ]; then
  title=$(echo "$body" | sed -n '/^---/,/^---/{/^---/n;p;q;}' )
fi

# Remove leading/trailing whitespace from the title (important for all cases)
title=$(echo "$title" | xargs)

if [ -z "$title" ]; then # check if title extraction failed.
    echo "Error: Failed to extract title using Pandoc."
    exit 1
fi

# 4. Remove YAML frontmatter (if any).
body=$(echo "$body" | sed '/^---/,/^---/d')

# 5. Remove the extracted title line from the body (to avoid duplication).
if [[ "$body" == *"# $title"* ]]; then  # Check if it was extracted as heading (# Title).
    body=$(echo "$body" | sed "1,/# $title/d")
elif [ -n "$title" ]; then   # Otherwise, check if title is not empty
    body=$(echo "$body" | sed "0,/$title/{/$title/d;}")
fi

# --- End Title Extraction Logic ---

# Output the formatted title and body
echo "# $title"
echo
echo "$body"