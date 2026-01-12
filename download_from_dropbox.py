import os
import shutil
import zipfile

import dropbox
from dotenv import load_dotenv
from dropbox import DropboxOAuth2FlowNoRedirect


def update_env_file(access_token, refresh_token):
    """
    Update .env file with new tokens, replacing existing values if present
    """
    # Load current environment variables
    load_dotenv()

    # Read the current .env file
    env_lines = []
    try:
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                env_lines = f.readlines()
    except Exception as e:
        print(f"Warning: Could not read .env file: {e}")
        env_lines = []

    # Process existing lines, removing the tokens we want to update
    new_lines = []
    access_token_found = False
    refresh_token_found = False

    for line in env_lines:
        line = line.strip()
        if line.startswith("DROPBOX_ACCESS_TOKEN="):
            if not access_token_found:
                new_lines.append(f"DROPBOX_ACCESS_TOKEN={access_token}")
                access_token_found = True
            # Skip this line (prevents duplicates)
        elif line.startswith("DROPBOX_REFRESH_TOKEN="):
            if not refresh_token_found:
                new_lines.append(f"DROPBOX_REFRESH_TOKEN={refresh_token}")
                refresh_token_found = True
            # Skip this line (prevents duplicates)
        elif line:  # Only keep non-empty lines
            new_lines.append(line)

    # Add tokens if they weren't in the file
    if not access_token_found:
        new_lines.append(f"DROPBOX_ACCESS_TOKEN={access_token}")
    if not refresh_token_found:
        new_lines.append(f"DROPBOX_REFRESH_TOKEN={refresh_token}")

    # Write the updated content back to .env
    with open(".env", "w") as f:
        f.write("\n".join(new_lines))

    print("Updated .env file with new tokens")


def get_dropbox_client():
    """
    Get a Dropbox client with proper OAuth2 handling
    This handles token refreshing more gracefully
    """
    load_dotenv()  # Load environment variables

    # Try to get the access token from environment
    access_token = os.environ.get("DROPBOX_ACCESS_TOKEN")
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")
    refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")

    # If we have a refresh token, use that to get a new access token
    if refresh_token and app_key and app_secret:
        try:
            # Initialize the client with the refresh token
            dbx = dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token,
            )
            # Test the connection (will auto-refresh if needed)
            dbx.users_get_current_account()
            print("Successfully authenticated using refresh token")
            return dbx
        except Exception as e:
            print(f"Error using refresh token: {e}")
            # Fall through to try access token or manual flow

    # If we have an access token, try using it directly
    if access_token:
        try:
            dbx = dropbox.Dropbox(access_token)
            # Test the connection
            dbx.users_get_current_account()
            print("Successfully authenticated using access token")
            return dbx
        except dropbox.exceptions.AuthError as e:
            print(f"Access token invalid or expired: {e}")
            # Fall through to manual flow

    # If we got here, we need to perform the OAuth flow manually
    if not app_key or not app_secret:
        raise ValueError(
            "App key and secret required for OAuth flow. Set DROPBOX_APP_KEY and DROPBOX_APP_SECRET environment variables."
        )

    # Start the OAuth flow with offline access to get a refresh token
    flow = DropboxOAuth2FlowNoRedirect(
        app_key, app_secret, token_access_type='offline'
    )
    authorize_url = flow.start()

    print("1. Go to: " + authorize_url)
    print("2. Click 'Allow' (you might have to log in first).")
    print("3. Copy the authorization code.")
    auth_code = input("Enter the authorization code here: ").strip()

    try:
        # This will get both access token and refresh token
        oauth_result = flow.finish(auth_code)
        access_token = oauth_result.access_token
        refresh_token = oauth_result.refresh_token

        # Check if we actually got a refresh token
        if not refresh_token:
            print("WARNING: No refresh token received from Dropbox.")
            print("Make sure your app has the 'offline access' permission")
            print("In the Dropbox App Console, check:")
            print("  - Under 'Permissions' tab, you have the necessary scopes")
            print(
                "  - Under 'Settings' tab, Access token expiration is set to 'Expiring access token'"
            )
            print("  - OAuth 2 allows 'offline access' (refresh token)")

        # Save tokens properly, replacing any existing ones
        update_env_file(access_token, refresh_token or "")

        print("Successfully saved new tokens to .env file")

        # Return a new client with the access token
        return dropbox.Dropbox(access_token)

    except Exception as e:
        raise ValueError(f"Error completing OAuth flow: {e}")


def download_shared_folder_as_zip(dbx, shared_link, local_zip_path):
    """Download a shared folder as a zip file"""
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


def download_and_process_dropbox_folder(shared_link, target_directory):
    """Complete workflow: download as zip, unzip, and clean up"""
    # Get authenticated client
    dbx = get_dropbox_client()

    # Determine the zip file path
    zip_path = os.path.join(target_directory, "downloaded.zip")

    # Step 1: Download the folder as a zip
    if download_shared_folder_as_zip(dbx, shared_link, zip_path):
        # Step 2: Unzip and clean up
        unzip_and_cleanup(zip_path, target_directory)
        return True
    return False


# Main execution
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Get shared link from environment variables
    shared_link = os.environ.get("DROPBOX_SHARED_LINK")

    if not shared_link:
        print("Error: DROPBOX_SHARED_LINK not found in environment variables")
        # Fall back to hardcoded link if needed
        shared_link = "https://www.dropbox.com/scl/fo/9os4f3413gzmj9v1t6mnr/h?rlkey=mrx4znkgvmqnmo4jd9vyetow0&st=jhb9agq2&dl=0"
        print(f"Using default shared link: {shared_link}")

    # Use the parent directory of this script's location as target
    # This script is in meditations/, so parent is upload_frcmed_to_web/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_directory = os.path.dirname(script_dir)

    # Run the complete workflow
    download_and_process_dropbox_folder(shared_link, target_directory)
