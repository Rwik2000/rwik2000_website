import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# --- USER CONFIGURATION: YOU MUST EDIT THESE VALUES ---

# Define the permissions your script needs.
# If you modify these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/spreadsheets"]

# The ID of your Google Sheet. You can find this in the URL of your sheet.
# e.g., "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit"
SPREADSHEET_ID = "1w4CuI4VMrMK58VlauItCY-N8KvJhMFfMkrbLHnI9Atk" 

# The name of the sheet (tab) where your CV file_id is stored.
SHEET_NAME = "CV" 

# The path to your local CV file that you want to upload.
# e.g., "/Users/rwik/Documents/Rwik_Rana_CV.pdf" or "C:\\Users\\Rwik\\Documents\\CV.pdf"
LOCAL_FILE_PATH = "output/generated_resume.pdf"

# The name you want the file to have on Google Drive.
DRIVE_FILE_NAME = "Rwik_Rana_CV.pdf"

# --- END OF USER CONFIGURATION ---


def get_credentials():
    """
    Handles user authentication and generates credentials.
    Creates a token.json file to store credentials for future runs.
    """
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
    """
    Uploads a file to Google Drive and returns the file ID.
    """
    try:
        print(f"Uploading '{file_path}' to Google Drive as '{file_name}'...")
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        
        file_metadata = {'name': file_name}
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        print(f"File uploaded successfully. File ID: {file_id}")
        return file_id
        
    except HttpError as error:
        print(f"An error occurred during file upload: {error}")
        return None
    except FileNotFoundError:
        print(f"Error: The file was not found at '{file_path}'. Please check the path.")
        return None

# --- NEW FUNCTION TO MAKE THE FILE PUBLIC ---
def share_file_publicly(service, file_id):
    """Makes the file publicly readable by anyone with the link."""
    try:
        print("Making file public...")
        permission = {'type': 'anyone', 'role': 'reader'}
        service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
        print("File is now publicly viewable by anyone with the link.")
    except HttpError as error:
        print(f"An error occurred while setting permissions: {error}")
# --- END OF NEW FUNCTION ---

def update_sheet(service, spreadsheet_id, sheet_name, new_file_id):
    """
    Updates cell A2 of the specified sheet with the new file ID.
    """
    try:
        range_to_update = f"{sheet_name}!A2"
        values = [[new_file_id]]
        body = {'values': values}

        print(f"Updating Google Sheet '{sheet_name}' at cell A2...")
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_to_update,
            valueInputOption="RAW",
            body=body
        ).execute()
        
        print(f"{result.get('updatedCells')} cell(s) updated successfully.")
        
    except HttpError as error:
        print(f"An error occurred while updating the sheet: {error}")


def main():
    """
    Main function to orchestrate the CV update process.
    """
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
        # --- ADDED STEP: SHARE THE FILE PUBLICLY ---
        share_file_publicly(drive_service, new_file_id)
        
        # --- EXISTING STEP: UPDATE THE SHEET ---
        update_sheet(sheets_service, SPREADSHEET_ID, SHEET_NAME, new_file_id)
        print("\nProcess complete! Your website will now show the updated and publicly accessible CV.")
    else:
        print("\nProcess failed. The Google Sheet was not updated.")


if __name__ == "__main__":
    main()

