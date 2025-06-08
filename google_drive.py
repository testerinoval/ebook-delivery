from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

def upload_and_share(local_path, drive_name, folder_id):
    creds = service_account.Credentials.from_service_account_file(
        os.path.join(os.path.dirname(__file__), "service-account.json"),
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": drive_name, "parents": [folder_id]}
    media = {"mimeType": "application/pdf", "body": open(local_path, "rb")}
    file = service.files().create(body=file_metadata,
                                  media_body=media,
                                  fields="id").execute()

    # make public
    service.permissions().create(fileId=file["id"],
                                 body={"role": "reader", "type": "anyone"}).execute()
    link = f"https://drive.google.com/uc?id={file['id']}&export=download"
    return link
