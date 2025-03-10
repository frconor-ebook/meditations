import os
import shutil
import zipfile

import dropbox
from dotenv import load_dotenv


def download_shared_folder_as_zip(access_token, shared_link, local_zip_path):
    """Download a shared folder as a zip file"""
    print(f"Connecting to Dropbox API...")
    dbx = dropbox.Dropbox(access_token)

    try:
        # Get shared folder metadata to find its path
        print(f"Getting metadata for shared link: {shared_link}")
        shared_metadata = dbx.sharing_get_shared_link_metadata(shared_link)

        # Get the path
        folder_path = shared_metadata.path_lower
        print(f"Resolved shared link to folder path: {folder_path}")

        # Make sure the target directory exists
        os.makedirs(os.path.dirname(local_zip_path), exist_ok=True)

        print(f"Downloading folder as zip: {folder_path}")
        # Download the folder as a zip file
        metadata, response = dbx.files_download_zip(folder_path)

        # Save the zip file
        with open(local_zip_path, "wb") as f:
            f.write(response.content)

        print(f"Successfully downloaded zip file to: {local_zip_path}")
        print(f"Zip size: {len(response.content) / (1024*1024):.2f} MB")
        return True

    except Exception as e:
        print(f"Error downloading folder as zip: {e}")
        return False


def unzip_and_cleanup(zip_file_path, extract_to):
    """
    Unzip the downloaded file, replace existing content, and clean up unnecessary files

    Parameters:
        zip_file_path (str): Path to the downloaded zip file
        extract_to (str): Directory to extract files to
    """
    try:
        # Create extraction directory if it doesn't exist
        os.makedirs(extract_to, exist_ok=True)

        # Get list of existing files/folders for cleanup
        existing_items = []
        if os.path.exists(extract_to):
            existing_items = [
                os.path.join(extract_to, item) for item in os.listdir(extract_to)
            ]

        print(f"Unzipping {zip_file_path} to {extract_to}...")
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            # Get list of all files in the zip
            file_count = len(zip_ref.namelist())
            print(f"Archive contains {file_count} files/folders")

            # Extract all files, overwriting existing ones
            zip_ref.extractall(path=extract_to)

        print("Unzipping completed successfully")

        # Clean up __MACOSX folder
        macosx_folder = os.path.join(extract_to, "__MACOSX")
        if os.path.exists(macosx_folder) and os.path.isdir(macosx_folder):
            print(f"Removing __MACOSX folder")
            shutil.rmtree(macosx_folder)

        # Clean up the zip file
        print(f"Removing zip file: {zip_file_path}")
        os.remove(zip_file_path)

        print("Cleanup completed successfully")
        return True

    except Exception as e:
        print(f"Error during unzip and cleanup: {e}")
        return False


def download_and_process_dropbox_folder(access_token, shared_link, target_directory):
    """Complete workflow: download as zip, unzip, and clean up"""
    # Determine the zip file path
    zip_path = os.path.join(target_directory, "downloaded.zip")

    # Step 1: Download the folder as a zip
    if download_shared_folder_as_zip(access_token, shared_link, zip_path):
        # Step 2: Unzip and clean up
        unzip_and_cleanup(zip_path, target_directory)
        return True
    return False


# Main execution
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Get credentials from environment variables
    access_token = os.environ.get("DROPBOX_ACCESS_TOKEN")
    shared_link = os.environ.get("DROPBOX_SHARED_LINK")

    # Check if credentials were loaded successfully
    if not access_token:
        print("Error: DROPBOX_ACCESS_TOKEN not found in environment variables")
        exit(1)

    if not shared_link:
        print("Error: DROPBOX_SHARED_LINK not found in environment variables")
        # Fall back to hardcoded link if needed
        shared_link = "https://www.dropbox.com/scl/fo/9os4f3413gzmj9v1t6mnr/h?rlkey=mrx4znkgvmqnmo4jd9vyetow0&st=jhb9agq2&dl=0"
        print(f"Using default shared link: {shared_link}")

    target_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web"

    # Run the complete workflow
    download_and_process_dropbox_folder(access_token, shared_link, target_directory)
