import mimetypes
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config

SCOPES = ['https://www.googleapis.com/auth/drive']

# Authenticate with service account
creds = service_account.Credentials.from_service_account_file(
    config.SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=creds)

def upload_and_share(file_path, file_name, folder_id=None):
    parents = [folder_id or config.GOOGLE_DRIVE_FOLDER_ID]
    file_metadata = {'name': file_name, 'parents': parents}

    mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    media = MediaFileUpload(file_path, mimetype=mime_type)

    # Upload
    file = drive_service.files().create(
        body=file_metadata, media_body=media, fields='id'
    ).execute()
    file_id = file.get('id')

    # Make public
    drive_service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    # Return a direct download link
    return f"https://drive.google.com/uc?id={file_id}&export=download"
