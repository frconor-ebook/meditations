import os
import shutil
import zipfile

import dropbox


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
    # First, get a direct access token from your app console
    # Go to https://www.dropbox.com/developers/apps
    # Select your app, then generate an access token
    access_token = "sl.u.AFlv8oDdz4r_Fp1yF0jIiGeYEKLGirDq3UgOPiRUHEEE2LyVwMdXpHvSC-ne4o9jG3uT8l4EmJIKrrjw4XIUgXQV2XOdJ8t--8GXEJNKpFpj29Nf0V6k5oiO6to_FuOez96MzUL2rwwsPUPasQgnAAr4Cqn82QnG01HnlC5h16-4McJ7FYWWY1Jq7_CjCLYjNDjiaa0ZNl_QV5-pPbLSNpaOqt54_n0_vD8RDDTsFPQyqR_uY6CHZTUvOps1Ezyofw3kwAMXdPUR9jTciEWRkcYkewj1W_IaR4qk1fiRMYUWUYy5vZpUp12VAXasIlSRmQt0zxhJRaZ75RhnhpNwT3whOiQn-7gdWouCxA-e2S-rmBDQeeMl35HlF_1s2yhZfJBS1Stxbm_ir3H83f4U_jmcf-B38Iw47wiPQXOJcNDdBf9oqh6VYEYbbbGvsFoPuTDoKvyUtJDubWi5zY_zRKzAeKMmqf3v3Pqz0YV_g3Jj27dMuo-igCNNvKvMVz0uXz_obQrnoQGmPkohp_MI2E4LpD3h1xJJNaenuiKhKECAzn8WXJBVqEY493C8uWz4tdON_8QjTIL1-HLrZ-119GQEt6KzjSgkzig4ZxmqeZR_FsL4nU00RATfm7rZpZN2s3Vseo1WTVb5_oUIO-WrSIzalXEy2wv7PYbWyZ8ggrx1odOdc8I2Y1XF7dzpWBLOD5PZVy77QWURuvxVlITjgdPdeFJDlrKTSIxYRhK63kTvtJuU2dXgF0Z9l36f649vhmq9VoS9vJckmdBB0F_aUqxKuiLBSqJZp5yr7qb5naslM0uHbYu553n_dKMjB9gtzClv-PnEp18gHLcB5XaLiuus68jywXLnvwPzwuOxeoVvIZXrlT8PGIUn5c42ezEgZe5YVm7WKT7_0Y5jEHYIDw6ir1V6dLT50Kb6-RtAz1uH8L-9NLqSUXfnWkgKm5zRclsHRzqQK7nnp4iFzCVMB706BZuVPy6Taa-ZlD1pqGMfN9Q9Bil3DNWxXYNF4gmDMQvHS-Y9WOJnomYDip0GdXqaQ9zF2PpFqJuQHjQtL7j0saLGDMG97kUekVqbvYEvz7ZnenVVKDn9SZU3ux5n5Hi64qpWGlDobzXRQi8nGup9VZvWfKpgzsSADXPLzKhUbzsKlgnIoutXNcjXJp-zNLG63shfbDekEAZRvsjrGP1eSZdphQhIQUtSoVPvPGVs-IxfpUvMWEtWqUDcqyZwVbcxyQsbevCZVHegqJfgYUiX9lVghcK_0ioV_yjcBjk7p6XwADz384zhsmk36VKHZZu7"

    shared_link = "https://www.dropbox.com/scl/fo/9os4f3413gzmj9v1t6mnr/h?rlkey=mrx4znkgvmqnmo4jd9vyetow0&st=jhb9agq2&dl=0"
    target_directory = "/Users/e_wijaya_ap/Desktop/upload_frcmed_to_web"

    # Run the complete workflow
    download_and_process_dropbox_folder(access_token, shared_link, target_directory)
