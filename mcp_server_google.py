import os.path
import base64
import mimetypes
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

def get_creds():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Credentials file {CREDENTIALS_FILE} not found.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

mcp = FastMCP("Google Workspace")

@mcp.tool()
def append_to_sheet(spreadsheet_id: str, values: list[str]) -> str:
    """Appends a row of values to a Google Sheet."""
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        body = {
            'values': [values]
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range="A1",
            valueInputOption="USER_ENTERED", body=body).execute()
            
        return f"Appended {result.get('updates').get('updatedCells')} cells."
    except Exception as e:
        return f"Error appending to sheet: {str(e)}"

@mcp.tool()
def send_email_with_attachment(to_email: str, subject: str, body: str, attachment_path: str = None) -> str:
    """Sends an email via Gmail, optionally with an attachment."""
    try:
        creds = get_creds()
        service = build('gmail', 'v1', credentials=creds)
        
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['From'] = 'me'
        message['Subject'] = subject
        
        if attachment_path and os.path.exists(attachment_path):
            ctype, encoding = mimetypes.guess_type(attachment_path)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed), so
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            
            with open(attachment_path, 'rb') as f:
                file_data = f.read()
                message.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))
        
        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        create_message = {
            'raw': encoded_message
        }
        
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        return f"Email sent. Message Id: {send_message['id']}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

@mcp.tool()
def create_doc_in_drive(name: str, content: str) -> str:
    """Creates a text file in Google Drive."""
    try:
        creds = get_creds()
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': name, 'mimeType': 'text/plain'}
        media = MediaFileUpload(None, mimetype='text/plain', resumable=True)
        # Note: MediaFileUpload usually takes a path. For string content, we might need a temp file or MediaIoBaseUpload
        # For simplicity, let's just write to a temp file first
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        media = MediaFileUpload(tmp_path, mimetype='text/plain')
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        os.unlink(tmp_path)
        return f"File created. ID: {file.get('id')}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

@mcp.tool()
def create_sheet(title: str) -> str:
    """Creates a new Google Sheet and returns its ID."""
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        return spreadsheet.get('spreadsheetId')
    except Exception as e:
        return f"Error creating sheet: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
