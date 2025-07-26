#!/usr/bin/env python3
"""
Google Drive Authentication Module
Handles OAuth flow and token management for Google Drive API
"""

import os
import json
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GoogleDriveAuth:
    def __init__(self):
        # Scopes define what permissions we're asking for
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.credentials_file = 'google_credentials.json'
        self.token_file = 'tokens/google_token.pickle'
        self.credentials = None
        self.service = None
        
        # Create tokens directory if it doesn't exist
        os.makedirs('tokens', exist_ok=True)
    
    def authenticate(self):
        """
        Authenticate with Google Drive API
        Returns True if successful, False otherwise
        """
        print("🔑 Authenticating with Google Drive...")
        
        # Check if we have valid credentials already
        if os.path.exists(self.token_file):
            print("📁 Found existing token, loading...")
            with open(self.token_file, 'rb') as token:
                self.credentials = pickle.load(token)
        
        # If credentials are invalid or don't exist, get new ones
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                print("🔄 Refreshing expired token...")
                try:
                    self.credentials.refresh(Request())
                except Exception as e:
                    print(f"❌ Failed to refresh token: {e}")
                    return self._do_oauth_flow()
            else:
                return self._do_oauth_flow()
            
            # Save the credentials for next time
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.credentials, token)
        
        # Build the service
        try:
            self.service = build('drive', 'v3', credentials=self.credentials)
            print("✅ Google Drive authentication successful!")
            return True
        except Exception as e:
            print(f"❌ Failed to build Google Drive service: {e}")
            return False
    
    def _do_oauth_flow(self):
        """
        Perform the OAuth flow to get new credentials
        """
        print("🌐 Starting OAuth flow...")
        
        if not os.path.exists(self.credentials_file):
            print(f"❌ Credentials file '{self.credentials_file}' not found!")
            print("Please download your OAuth credentials from Google Cloud Console")
            print("and save them as 'google_credentials.json' in the project root.")
            return False
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, self.SCOPES)
            self.credentials = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.credentials, token)
            
            return True
        except Exception as e:
            print(f"❌ OAuth flow failed: {e}")
            return False
    
    def get_service(self):
        """
        Get the authenticated Google Drive service
        """
        if not self.service:
            if not self.authenticate():
                return None
        return self.service
    
    def test_connection(self):
        """
        Test the connection by getting user info
        """
        service = self.get_service()
        if not service:
            return False
        
        try:
            # Get user info to test connection
            about = service.about().get(fields="user").execute()
            user = about.get('user', {})
            print(f"👤 Connected as: {user.get('displayName', 'Unknown')} ({user.get('emailAddress', 'Unknown')})")
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

def main():
    """
    Test function - run this file directly to test authentication
    """
    print("🧪 Testing Google Drive authentication...")
    auth = GoogleDriveAuth()
    
    if auth.authenticate():
        auth.test_connection()
    else:
        print("❌ Authentication failed")

if __name__ == "__main__":
    main()