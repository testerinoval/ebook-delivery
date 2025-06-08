from google_drive import upload_and_share
import config

# Make sure you have a file named 'test.pdf' in this folder.
link = upload_and_share('test.pdf', 'TestUpload.pdf', config.GOOGLE_DRIVE_FOLDER_ID)
print("Drive link:", link)
