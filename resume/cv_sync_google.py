import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# --- USER CONFIGURATION: YOU MAY EDIT THESE VALUES ---

# If you need to delete files not created by this script, change drive scope to:
# "https://www.googleapis.com/auth/drive" and delete token.json once to re-consent.
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

SPREADSHEET_ID = "1w4CuI4VMrMK58VlauItCY-N8KvJhMFfMkrbLHnI9Atk"
SHEET_NAME = "CV"

LOCAL_FILE_PATH = "output/generated_resume.pdf"
DRIVE_FILE_NAME = "Rwik_Rana_CV.pdf"

# Trash old files by default (safer). Set True to permanently delete.
PERMANENT_DELETE = False

# --- END OF USER CONFIGURATION ---


def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def upload_file_to_drive(service, file_path, file_name):
    """Uploads a file to Google Drive and returns the file ID."""
    try:
        print(f"Uploading '{file_path}' to Google Drive as '{file_name}'...")
        media = MediaFileUpload(file_path, mimetype="application/pdf")
        file_metadata = {"name": file_name}
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_id = file.get("id")
        print(f"File uploaded successfully. File ID: {file_id}")
        return file_id
    except HttpError as error:
        print(f"An error occurred during file upload: {error}")
        return None
    except FileNotFoundError:
        print(f"Error: The file was not found at '{file_path}'. Please check the path.")
        return None


def share_file_publicly(service, file_id):
    """Makes the file publicly readable by anyone with the link."""
    try:
        print("Making file public...")
        permission = {"type": "anyone", "role": "reader"}
        service.permissions().create(fileId=file_id, body=permission).execute()
        print("File is now publicly viewable by anyone with the link.")
    except HttpError as error:
        print(f"An error occurred while setting permissions: {error}")


# --- NEW: find + delete previous resume files ---
def _find_files_by_name(service, name):
    """Return list of {id, name, createdTime} for non-trashed files matching name."""
    results = []
    page_token = None
    query = f"name = '{name}' and trashed = false"
    fields = "nextPageToken, files(id, name, createdTime)"
    try:
        while True:
            resp = service.files().list(q=query, fields=fields, pageToken=page_token).execute()
            results.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    except HttpError as error:
        print(f"Error searching files: {error}")
    return results


def _trash_or_delete_file(service, file_id, permanent=False):
    """Trash (default) or permanently delete a Drive file."""
    try:
        if permanent:
            service.files().delete(fileId=file_id).execute()
        else:
            service.files().update(fileId=file_id, body={"trashed": True}).execute()
    except HttpError as error:
        print(f"Error deleting file {file_id}: {error}")


def delete_previous_resume_files(service, file_name, keep_file_id, permanent=False):
    """Delete/trash all files named file_name except keep_file_id. Returns count removed."""
    candidates = _find_files_by_name(service, file_name)
    removed = 0
    for f in candidates:
        if f["id"] == keep_file_id:
            continue
        _trash_or_delete_file(service, f["id"], permanent=permanent)
        removed += 1
    action = "permanently deleted" if permanent else "moved to Trash"
    print(f"{removed} old file(s) {action}.")
    return removed
# --- END NEW ---


def update_sheet(service, spreadsheet_id, sheet_name, new_file_id):
    """Updates cell A2 of the specified sheet with the new file ID."""
    try:
        range_to_update = f"{sheet_name}!A2"
        values = [[new_file_id]]
        body = {"values": values}
        print(f"Updating Google Sheet '{sheet_name}' at cell A2...")
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_to_update, valueInputOption="RAW", body=body
        ).execute()
        print(f"{result.get('updatedCells')} cell(s) updated successfully.")
    except HttpError as error:
        print(f"An error occurred while updating the sheet: {error}")


def main():
    creds = get_credentials()
    if not creds:
        print("Could not authenticate. Exiting.")
        return

    try:
        drive_service = build("drive", "v3", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)
    except HttpError as error:
        print(f"An error occurred while building the services: {error}")
        return

    new_file_id = upload_file_to_drive(drive_service, LOCAL_FILE_PATH, DRIVE_FILE_NAME)

    if new_file_id:
        # Remove previous files with the same name (except the new one)
        delete_previous_resume_files(
            drive_service, DRIVE_FILE_NAME, keep_file_id=new_file_id, permanent=PERMANENT_DELETE
        )

        # Make the surviving (new) file public
        share_file_publicly(drive_service, new_file_id)

        # Update the Sheet with the fresh file ID
        update_sheet(sheets_service, SPREADSHEET_ID, SHEET_NAME, new_file_id)

        print("\nProcess complete! Your website will now show the updated and publicly accessible CV.")
    else:
        print("\nProcess failed. The Google Sheet was not updated.")


if __name__ == "__main__":
    main()
