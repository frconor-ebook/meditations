#!/usr/bin/env python3
"""
Check which DocX files have changed and need conversion.
Used by the conversion script for incremental processing.
"""

import argparse
import os
import sys

# Add parent directory to path to import file_manifest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from file_manifest import get_changed_files, load_manifest, save_manifest, compute_file_hash


def get_files_to_convert(source_dir, dest_dir, manifest_dir, force=False):
    """
    Determine which files need to be converted.

    Args:
        source_dir: Directory containing source DocX files
        dest_dir: Directory containing converted markdown files
        manifest_dir: Directory where manifest is stored
        force: If True, return all files

    Returns:
        tuple: (files_to_convert, files_to_delete, new_hashes)
    """
    manifest = load_manifest(manifest_dir)

    if force:
        # Return all DocX files
        all_files = []
        new_hashes = {}
        for filename in os.listdir(source_dir):
            if filename.lower().endswith(('.doc', '.docx')):
                all_files.append(filename)
                filepath = os.path.join(source_dir, filename)
                file_hash = compute_file_hash(filepath)
                if file_hash:
                    new_hashes[filename] = file_hash
        return all_files, [], new_hashes

    # Get stored hashes
    old_hashes = manifest.get("docx_hashes", {})

    # Compute current hashes for all DocX files
    current_hashes = {}
    for filename in os.listdir(source_dir):
        if filename.lower().endswith(('.doc', '.docx')):
            filepath = os.path.join(source_dir, filename)
            file_hash = compute_file_hash(filepath)
            if file_hash:
                current_hashes[filename] = file_hash

    # Determine which files have changed
    files_to_convert = []
    for filename, current_hash in current_hashes.items():
        old_hash = old_hashes.get(filename)
        if old_hash != current_hash:
            files_to_convert.append(filename)
        else:
            # Also check if the output file exists
            md_filename = os.path.splitext(filename)[0] + ".md"
            md_path = os.path.join(dest_dir, md_filename)
            if not os.path.exists(md_path):
                files_to_convert.append(filename)

    # Find deleted files (need to remove their markdown counterparts)
    files_to_delete = []
    for filename in old_hashes:
        if filename not in current_hashes:
            md_filename = os.path.splitext(filename)[0] + ".md"
            files_to_delete.append(md_filename)

    return files_to_convert, files_to_delete, current_hashes


def main():
    parser = argparse.ArgumentParser(
        description="Check which DocX files have changed and need conversion."
    )
    parser.add_argument("source_dir", help="Directory containing source DocX files")
    parser.add_argument("dest_dir", help="Directory for converted markdown files")
    parser.add_argument("--manifest-dir", help="Directory for manifest file",
                        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force processing of all files")
    parser.add_argument("--output", "-o", choices=["convert", "delete", "count", "update-manifest"],
                        default="convert",
                        help="What to output: 'convert' (files to convert), "
                             "'delete' (files to delete), 'count' (summary), "
                             "'update-manifest' (save new hashes)")
    args = parser.parse_args()

    files_to_convert, files_to_delete, current_hashes = get_files_to_convert(
        args.source_dir, args.dest_dir, args.manifest_dir, args.force
    )

    if args.output == "convert":
        # Output list of files to convert (one per line)
        for f in files_to_convert:
            print(f)
    elif args.output == "delete":
        # Output list of markdown files to delete
        for f in files_to_delete:
            print(f)
    elif args.output == "count":
        # Output summary
        total = len(current_hashes)
        to_convert = len(files_to_convert)
        to_delete = len(files_to_delete)
        unchanged = total - to_convert
        print(f"Total files: {total}")
        print(f"To convert: {to_convert}")
        print(f"Unchanged: {unchanged}")
        print(f"To delete: {to_delete}")
    elif args.output == "update-manifest":
        # Save the new hashes to manifest
        manifest = load_manifest(args.manifest_dir)
        manifest["docx_hashes"] = current_hashes
        save_manifest(args.manifest_dir, manifest)
        print(f"Updated manifest with {len(current_hashes)} file hashes.")


if __name__ == "__main__":
    main()
