import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def debug_auth():
    print("--- Google Auth Debugger ---")
    
    # 1. Check Credentials File
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} not found!")
        return
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            creds_data = json.load(f)
            # Handle both "installed" and "web" formats
            key = 'installed' if 'installed' in creds_data else 'web'
            project_id = creds_data.get(key, {}).get('project_id')
            print(f"OK: {CREDENTIALS_FILE} found. Project ID: {project_id}")
    except Exception as e:
        print(f"Warning: Could not read Project ID: {e}")

    # 2. Check Token File
    creds = None
    if os.path.exists(TOKEN_FILE):
        print(f"INFO: {TOKEN_FILE} found. Checking scopes...")
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
                print(f"Current Token Scopes: {token_data.get('scopes')}")
                
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"ERROR reading token file: {e}")
    else:
        print(f"INFO: {TOKEN_FILE} not found. You will need to login.")

    # 3. Refresh or Login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("INFO: Token expired, refreshing...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"ERROR refreshing token: {e}")
                print("Action: Deleting invalid token.json")
                os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            print("INFO: Initiating new login flow...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save new token
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            print("INFO: New login successful. Token saved.")

    # 4. Test API Access
    print("\n--- Testing API Access ---")
    
    # Test Drive API first (simpler)
    try:
        print("Testing Drive API (List Files)...")
        drive_service = build('drive', 'v3', credentials=creds)
        results = drive_service.files().list(pageSize=1, fields="nextPageToken, files(id, name)").execute()
        print("SUCCESS: Drive API is working.")
    except Exception as e:
        print(f"FAIL: Drive API Error: {e}")

    # Test Sheets API
    try:
        service = build('sheets', 'v4', credentials=creds)
        spreadsheet = {'properties': {'title': 'Debug Test Sheet'}}
        print("Testing Sheets API (Create Sheet)...")
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        print(f"SUCCESS! Created sheet with ID: {spreadsheet.get('spreadsheetId')}")
    except Exception as e:
        print(f"FAIL: Sheets API Error: {e}")
        if hasattr(e, 'content'):
            print(f"Full Error Content: {e.content}")
        if "403" in str(e):
            print("\nPOSSIBLE CAUSES:")
            print("1. Google Sheets API is NOT enabled in Cloud Console.")
            print("2. You did not check the 'See, edit, create, and delete...' box during login.")
            print("3. Your User is not added to 'Test Users' in OAuth Consent Screen.")

if __name__ == "__main__":
    debug_auth()
