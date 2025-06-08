# google_drive.py

from dotenv import load_dotenv
import os, json

# 1) load from .env (on VM) or from Render's env
load_dotenv()

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 2) grab the JSON text from the environment
sa_json = os.getenv("SERVICE_ACCOUNT_JSON")
if not sa_json:
    raise RuntimeError("SERVICE_ACCOUNT_JSON must be set")

info = json.loads(sa_json)

# 3) create credentials & Drive service
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
service = build("drive", "v3", credentials=creds)


def upload_and_share(local_path, name, folder_id):
    """
    Uploads a file at `local_path` into `folder_id` on Drive,
    makes it publicly readable, and returns a download link.
    """
    media = MediaFileUpload(str(local_path), resumable=True)
    metadata = {"name": name, "parents": [folder_id]}

    created = (
        service.files()
               .create(body=metadata, media_body=media, fields="id")
               .execute()
    )
    file_id = created.get("id")

    # share publicly
    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    # direct‐download link
    return f"https://drive.google.com/uc?id={file_id}&export=download"
