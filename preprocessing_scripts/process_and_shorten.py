import csv
import json
import os
from typing import List, Tuple

# Import the function from create_long_urls.py
from create_long_urls import create_long_urls
from dotenv import load_dotenv
from shorten_urls import create_custom_short_url


def process_long_urls_to_csv(
    long_urls_file: str, output_dir: str, tinyurl_api_token: str, groq_api_key: str
):
    """
    Processes a JSON file containing long URLs, shortens them, and saves the results to a CSV file.
    Also, checks for existing shortened URLs in the CSV and skips them if they already exist.

    Args:
        long_urls_file: Path to the JSON file containing long URLs.
        output_dir: Path to the directory where the output CSV file will be saved.
        tinyurl_api_token: Your TinyURL API token.
        groq_api_key: Your Groq API key.
    """

    try:
        with open(long_urls_file, "r") as f:
            long_urls = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {long_urls_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {long_urls_file}")
        return

    output_csv = os.path.join(output_dir, "shortened_urls.csv")
    existing_urls = set()

    # Check for existing URLs in the CSV file
    if os.path.exists(output_csv):
        with open(output_csv, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                existing_urls.add(row["long_url"])

    new_results: List[Tuple[str, str]] = []

    for long_url in long_urls:
        if long_url in existing_urls:
            print(f"Skipping already shortened URL: {long_url}")
            continue

        print(f"Processing: {long_url}")
        short_url = create_custom_short_url(long_url, tinyurl_api_token, groq_api_key)
        if short_url:
            new_results.append((long_url, short_url))
        else:
            print(f"Failed to shorten: {long_url}")

    # Append new results to CSV
    with open(output_csv, "a", newline="") as csvfile:
        fieldnames = ["long_url", "short_url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if csvfile.tell() == 0:  # Write header only if file is empty
            writer.writeheader()

        for long_url, short_url in new_results:
            writer.writerow({"long_url": long_url, "short_url": short_url})

    print(f"Shortened URLs saved to {output_csv}")


if __name__ == "__main__":
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")
    tinyurl_api_token = os.getenv("TINYURL_API_TOKEN")

    # Define directories and file paths
    # Path to the meditations input JSON used by create_long_urls.py
    meditations_input_file = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/data/meditations.json"
    # Directory where long_urls.json and the CSV will be stored
    output_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/etc"

    # Step 1: Create the long URLs file from meditations.json
    create_long_urls(meditations_input_file, output_directory)

    # Step 2: Process the generated long URLs to create the CSV of shortened URLs
    long_urls_file = os.path.join(output_directory, "long_urls.json")
    process_long_urls_to_csv(
        long_urls_file, output_directory, tinyurl_api_token, groq_api_key
    )
