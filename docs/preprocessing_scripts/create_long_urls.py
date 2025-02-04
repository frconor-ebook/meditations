import json
import os
import urllib.parse


def create_long_urls(input_file, output_dir):
    """
    Processes a JSON file containing meditation entries, creates long URLs based on slugs,
    and decodes the URLs for display (not properly percent-encoded), saving them as a new JSON file.

    Args:
        input_file: Path to the input JSON file (meditations.json).
        output_dir: Path to the directory where the output JSON file (long_urls.json) will be saved.
    """

    try:
        with open(input_file, "r") as f:
            meditations = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {input_file}")
        return

    long_urls = []

    # Convert to entries array
    entries = [{"key": i, "value": meditations[i]} for i in range(len(meditations))]

    for entry in entries:
        slug = entry["value"]["slug"]
        long_url = f"https://frconor-ebook.github.io/meditations/homilies/{slug}/"

        # Decode the URL for display
        decoded_url = urllib.parse.unquote(long_url)

        long_urls.append(decoded_url)

    output_file = os.path.join(output_dir, "long_urls.json")
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(output_file, "w") as f:
            json.dump(
                long_urls, f, indent=2, ensure_ascii=False
            )  # Ensure non-ASCII characters are not escaped
        print(f"Long URLs saved to {output_file}")
    except Exception as e:
        print(f"Error: Failed to save long URLs to {output_file}. Error: {e}")


if __name__ == "__main__":
    input_json_file = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/data/meditations.json"
    output_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web/meditations/etc"
    create_long_urls(input_json_file, output_directory)
