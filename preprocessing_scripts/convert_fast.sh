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

# Extract metadata (including title) and body using Pandoc
metadata=$(pandoc -s --metadata-file=/dev/null --to=markdown "$input_docx" -M title 2>/dev/null)
body=$(pandoc -s --to=markdown "$input_docx" 2>/dev/null)

# Check if Pandoc extracted the title successfully (using sed)
title=$(echo "$metadata" | sed -n 's/^title: //p')
if [ -z "$title" ]; then
    echo "Error: Failed to extract title using Pandoc.  Check document properties."
    exit 1
fi

# Check if Pandoc converted body successfully.
if [ -z "$body" ]; then
    echo "Error: Failed to convert body from '$input_docx' using Pandoc."
    exit 1
fi

# Output the extracted title and converted body
{
    echo "# $title"
    echo
    echo "$body"
} | sed '/^convert .* as a Writer document/d'