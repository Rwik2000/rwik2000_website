# Automated CV Updater for Personal Website

This project contains a Python script that automates the process of keeping your CV updated on your personal website. It performs three main tasks in a single execution:

1.  **Uploads** a specified PDF file (your CV) to your Google Drive.
2.  **Sets the file's permission** to "Anyone with the link can view" so it can be embedded on your public website.
3.  **Updates a Google Sheet** with the new Google Drive file ID, which your website reads from to display the latest CV.

This eliminates the need to manually upload, share, and copy/paste file IDs every time you update your resume.

## Prerequisites

Before you begin, ensure you have the following:

* A Google Account.
* Python 3.6 or newer installed on your computer.
* Your updated CV saved as a PDF file on your local machine.

## Setup Instructions

This is a one-time setup process that involves configuring Google's services to allow the Python script to manage your files and sheets securely.

### Part 1: Configure Google Cloud & Sheets

1.  **Enable APIs in Google Cloud:**
    * Go to the [Google Cloud Console](https://console.cloud.google.com/).
    * Create a new project or select an existing one.
    * In the navigation menu (☰), go to **APIs & Services > Library**.
    * Search for and **enable** the following two APIs:
        1.  `Google Drive API`
        2.  `Google Sheets API`

2.  **Create OAuth Credentials:**
    * In the navigation menu, go to **APIs & Services > Credentials**.
    * Click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
    * For the **Application type**, choose **Desktop app**.
    * Give it a name (e.g., "CV Updater Script") and click **CREATE**.

3.  **Download `credentials.json`:**
    * After creation, a pop-up will appear. Click the **DOWNLOAD JSON** button.
    * Rename the downloaded file to `credentials.json`.
    * **Important:** Place this `credentials.json` file in the same directory where you will save the `update_cv.py` script. Treat this file like a password; do not share it publicly.

4.  **Set Up Google Sheet:**
    * Open the Google Sheet that your website uses to fetch data.
    * Create a new sheet (tab) and name it **`CV`**.
    * In cell `A1` of this sheet, type the header: `file_id`.
    * The script will automatically populate cell `A2` with the correct ID.
    * Note down your **Spreadsheet ID** from the URL: `https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID_HERE/edit`

### Part 2: Prepare the Python Environment

1.  **Install Libraries:**
    * Open your terminal or command prompt.
    * Run the following command to install the necessary Google API client libraries for Python:
        ```bash
        pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
        ```

2.  **Configure the Script:**
    * Open the `update_cv.py` file in a text editor.
    * Fill in the variables in the **`--- USER CONFIGURATION ---`** section at the top of the file:
        * `SPREADSHEET_ID`: The ID you noted from your Google Sheet's URL.
        * `SHEET_NAME`: Should be `"CV"` (or whatever you named the tab).
        * `LOCAL_FILE_PATH`: The full path to the CV PDF file on your computer (e.g., `/Users/yourname/Documents/My_CV.pdf`).
        * `DRIVE_FILE_NAME`: The name you want the file to have once uploaded to Google Drive (e.g., `"Rwik_Rana_CV.pdf"`).

### Part 3: First-Time Execution and Authorization

1.  **Run the Script:**
    * Open your terminal and navigate to the folder containing `update_cv.py` and `credentials.json`.
    * Execute the script:
        ```bash
        python update_cv.py
        ```

2.  **Authorize the Application (First Run Only):**
    * A browser window will automatically open, asking you to log in to your Google Account.
    * You will likely see an **"Access blocked: This app has not completed the Google verification process"** error. This is normal.
        * **Solution:** Go back to your Google Cloud Console, navigate to **APIs & Services > OAuth consent screen**, and under **Test users**, click **+ ADD USERS**. Add your own Google email address.
    * Run the script again. This time, you will see a **"Google hasn’t verified this app"** warning.
        * Click **Advanced**.
        * Click **Go to "Your App Name" (unsafe)**.
        * On the final screen, review the permissions and click **Allow**.

3.  **Completion:**
    * The script will complete the execution in your terminal, and you will see success messages for the file upload, sharing, and sheet update.
    * A `token.json` file will now be present in your folder. This file securely stores your authorization, so you won't have to log in through the browser again.

## Usage for Future Updates

Once the setup is complete, updating your CV is as simple as:

```bash
chmod +x build_resume.sh
./build_resume.sh
```


The script will handle the rest automatically.