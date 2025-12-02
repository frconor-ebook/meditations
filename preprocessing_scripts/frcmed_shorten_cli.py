#!/usr/bin/env python3
"""CLI tool to shorten Fr. Conor meditation URLs."""

import argparse
import os
import sys

from dotenv import load_dotenv
from shorten_urls import create_custom_short_url

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


def main():
    parser = argparse.ArgumentParser(
        description="Shorten Fr. Conor meditation URLs with custom TinyURL aliases"
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="One or more URLs to shorten"
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Disable automatic clipboard copy"
    )

    args = parser.parse_args()

    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    tinyurl_api_token = os.getenv("TINYURL_API_TOKEN")

    if not gemini_api_key or not tinyurl_api_token:
        print("Error: Missing GEMINI_API_KEY or TINYURL_API_TOKEN in .env", file=sys.stderr)
        sys.exit(1)

    results = []
    for url in args.urls:
        short_url = create_custom_short_url(url, tinyurl_api_token, gemini_api_key)
        if short_url:
            print(short_url)
            results.append(short_url)
        else:
            print(f"Failed to shorten: {url}", file=sys.stderr)
            sys.exit(1)

    # Copy to clipboard (automatic by default)
    if results and not args.no_copy:
        if CLIPBOARD_AVAILABLE:
            clipboard_text = "\n".join(results)
            pyperclip.copy(clipboard_text)
            print("(Copied to clipboard)")
        else:
            print("(Clipboard not available - install pyperclip: pip install pyperclip)", file=sys.stderr)


if __name__ == "__main__":
    main()
