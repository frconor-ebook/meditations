#!/bin/bash
# We don't use this code anymore. It's too slow. We use convert_fast.sh instead.

# Script to extract the title and body from a DOCX file
# - Uses LibreOffice to extract the first line as the title
# - Uses Pandoc to convert the body to Markdown format
# - Outputs the formatted document to STDOUT

# Ensure an input file is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_docx_file>"
    exit 1
fi

# Assign the input DOCX file from command-line argument
input_docx="$1"

# Verify that the input file exists
if [ ! -f "$input_docx" ]; then
    echo "Error: File '$input_docx' not found!"
    exit 1
fi

# Create a temporary file to store extracted text
temp_file=$(mktemp)

# Use LibreOffice to convert DOCX to a plain text file, suppressing output
# LibreOffice will save the converted file in the same directory as the input
# This is the slowest part of the script. It's better to use convert_fast.sh
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to "txt:Text (encoded):UTF8" "$input_docx" > /dev/null 2>&1


# Identify the converted text file (LibreOffice names it after the original file)
temp_file_name=$(basename "$input_docx" .docx).txt
# echo $temp_file_name

# Move the converted text file to the temporary file location for processing
mv "$temp_file_name" "$temp_file"

# Extract the first line from the text file as the title, removing any non-printable characters
title=$(head -n 1 "$temp_file" | sed 's/[^[:print:]]//g')

# Ensure title extraction was successful
if [ -z "$title" ]; then
    rm -f "$temp_file"
    echo "Error: Failed to extract title from '$input_docx'."
    exit 1
fi

# Convert the DOCX body content to Markdown format using Pandoc
# The conversion result is stored in the `body` variable
body=$(pandoc -t markdown "$input_docx" 2>/dev/null)

# Verify that the Pandoc conversion was successful
if [ -z "$body" ]; then
    rm -f "$temp_file"
    echo "Error: Failed to convert body from '$input_docx' using Pandoc."
    exit 1
fi

# Clean up the temporary file
# rm -f "$temp_file"

# Output the extracted title and converted body in Markdown format
# - The title is prefixed with '#' to format it as a Markdown header
# - The body content follows, separated by a blank line
{
    echo "# $title"
    echo
    echo "$body"
} | sed '/^convert .* as a Writer document/d'  # Remove any unwanted Pandoc conversion messages
