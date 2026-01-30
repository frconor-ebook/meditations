"""
File Manifest Utility

Manages file checksums for incremental processing in the FRCMED pipeline.
Tracks file changes using SHA256 hashes to avoid redundant processing.
"""

import hashlib
import json
import os
from pathlib import Path


MANIFEST_FILENAME = ".file_manifest.json"


def get_manifest_path(base_dir):
    """Get the path to the manifest file."""
    return os.path.join(base_dir, MANIFEST_FILENAME)


def load_manifest(base_dir):
    """
    Load the file manifest from disk.

    Returns:
        dict: Manifest with structure:
            {
                "dropbox_hashes": {"filename": "content_hash", ...},
                "docx_hashes": {"filename": "sha256_hash", ...},
                "markdown_hashes": {"filename": "sha256_hash", ...}
            }
    """
    manifest_path = get_manifest_path(base_dir)
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load manifest: {e}")

    return {
        "dropbox_hashes": {},
        "docx_hashes": {},
        "markdown_hashes": {}
    }


def save_manifest(base_dir, manifest):
    """Save the file manifest to disk."""
    manifest_path = get_manifest_path(base_dir)
    try:
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save manifest: {e}")


def compute_file_hash(filepath):
    """
    Compute SHA256 hash of a file.

    Args:
        filepath: Path to the file

    Returns:
        str: Hex digest of SHA256 hash, or None if file doesn't exist
    """
    if not os.path.exists(filepath):
        return None

    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except IOError:
        return None


def get_changed_files(source_dir, manifest_key, manifest):
    """
    Get list of files that have changed since last processing.

    Args:
        source_dir: Directory containing source files
        manifest_key: Key in manifest to use for comparison ("docx_hashes" or "markdown_hashes")
        manifest: The loaded manifest dict

    Returns:
        tuple: (changed_files, deleted_files, current_hashes)
            - changed_files: List of files that are new or modified
            - deleted_files: List of files that no longer exist
            - current_hashes: Dict of current file hashes
    """
    if not os.path.exists(source_dir):
        return [], [], {}

    old_hashes = manifest.get(manifest_key, {})
    current_hashes = {}
    changed_files = []

    # Check all files in source directory
    for filename in os.listdir(source_dir):
        filepath = os.path.join(source_dir, filename)
        if os.path.isfile(filepath):
            current_hash = compute_file_hash(filepath)
            if current_hash:
                current_hashes[filename] = current_hash

                # File is changed if it's new or has different hash
                old_hash = old_hashes.get(filename)
                if old_hash != current_hash:
                    changed_files.append(filename)

    # Find deleted files
    deleted_files = [f for f in old_hashes if f not in current_hashes]

    return changed_files, deleted_files, current_hashes


def update_manifest_hashes(base_dir, manifest_key, hashes):
    """
    Update a specific hash section in the manifest.

    Args:
        base_dir: Base directory where manifest is stored
        manifest_key: Key to update ("dropbox_hashes", "docx_hashes", or "markdown_hashes")
        hashes: Dict of filename -> hash
    """
    manifest = load_manifest(base_dir)
    manifest[manifest_key] = hashes
    save_manifest(base_dir, manifest)


def clear_manifest(base_dir):
    """Clear the manifest file (for --force mode)."""
    manifest_path = get_manifest_path(base_dir)
    if os.path.exists(manifest_path):
        os.remove(manifest_path)
        print(f"Cleared manifest: {manifest_path}")


if __name__ == "__main__":
    # Test the module
    import sys

    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
    else:
        test_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"Testing file manifest in: {test_dir}")

    manifest = load_manifest(test_dir)
    print(f"Current manifest keys: {list(manifest.keys())}")

    for key, hashes in manifest.items():
        print(f"  {key}: {len(hashes)} entries")
