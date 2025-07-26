#!/usr/bin/env python3
"""
Adobe Lightroom CC Authentication Module
Handles OAuth flow and token management for Adobe Lightroom API
"""

import os
import json
import webbrowser
import urllib.parse
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables
load_dotenv()
console = Console()

class AdobeLightroomAuth:
    def __init__(self):
        self.client_id = os.getenv('ADOBE_CLIENT_ID')
        self.client_secret = os.getenv('ADOBE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('ADOBE_REDIRECT_URI', 'http://localhost:8080/callback')
        self.token_file = 'tokens/adobe_token.json'
        
        # Adobe API endpoints
        self.auth_url = 'https://ims-na1.adobelogin.com/ims/authorize/v2'
        self.token_url = 'https://ims-na1.adobelogin.com/ims/token/v3'
        self.api_base = 'https://lr.adobe.io'
        
        # Required scopes for Lightroom
        self.scopes = ['openid', 'lr_partner_apis']
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
        
        # Create tokens directory if it doesn't exist
        os.makedirs('tokens', exist_ok=True)
        
        # Validate credentials
        if not self.client_id or not self.client_secret:
            print("❌ Adobe credentials not found in .env file!")
            print("Please add ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET to your .env file")
    
    def authenticate(self):
        """
        Authenticate with Adobe Lightroom API
        Returns True if successful, False otherwise
        """
        print("🎨 Authenticating with Adobe Lightroom...")
        
        if not self.client_id or not self.client_secret:
            return False
        
        # Check if we have valid tokens already
        if self._load_tokens():
            if self._is_token_valid():
                print("✅ Using existing valid token")
                return True
            elif self.refresh_token:
                print("🔄 Refreshing expired token...")
                if self._refresh_access_token():
                    return True
        
        # Need to do OAuth flow
        return self._do_oauth_flow()
    
    def _load_tokens(self):
        """
        Load tokens from file
        """
        if not os.path.exists(self.token_file):
            return False
        
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            # Parse expiration time
            expires_str = token_data.get('expires_at')
            if expires_str:
                self.token_expires = datetime.fromisoformat(expires_str)
            
            return bool(self.access_token)
        except Exception as e:
            print(f"⚠️  Warning: Could not load Adobe tokens: {e}")
            return False
    
    def _save_tokens(self, token_response):
        """
        Save tokens to file
        """
        try:
            # Calculate expiration time
            expires_in = token_response.get('expires_in', 3600)  # Default 1 hour
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            token_data = {
                'access_token': token_response['access_token'],
                'refresh_token': token_response.get('refresh_token', self.refresh_token),
                'expires_at': expires_at.isoformat(),
                'token_type': token_response.get('token_type', 'Bearer')
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            # Update instance variables
            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            self.token_expires = expires_at
            
            print("💾 Adobe tokens saved successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to save Adobe tokens: {e}")
            return False
    
    def _is_token_valid(self):
        """
        Check if current access token is valid
        """
        if not self.access_token or not self.token_expires:
            return False
        
        # Check if token expires in next 5 minutes
        return datetime.now() < (self.token_expires - timedelta(minutes=5))
    
    def _do_oauth_flow(self):
        """
        Perform the OAuth flow to get new tokens
        """
        print("🌐 Starting Adobe OAuth flow...")
        
        # Build authorization URL
        auth_params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ','.join(self.scopes),
            'response_type': 'code',
            'state': 'lightroom_sync_state'  # CSRF protection
        }
        
        auth_url = f"{self.auth_url}?{urllib.parse.urlencode(auth_params)}"
        
        print("🔗 Opening browser for Adobe authentication...")
        print("If browser doesn't open automatically, copy and paste this URL:")
        print(f"   {auth_url}")
        print()
        print("📋 INSTRUCTIONS:")
        print("1. Sign in to Adobe in the browser")
        print("2. Grant permissions to the app")
        print("3. You'll be redirected to a page (might show an error - that's OK!)")
        print("4. Look at the URL in your browser's address bar")
        print("5. Find the part that says '?code=XXXXXXX' or '&code=XXXXXXX'")
        print("6. Copy just the code part (after 'code=' and before any '&')")
        print()
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Get the authorization code from user input
        print("🔑 STEP-BY-STEP INSTRUCTIONS:")
        print("1. Copy the authorization code from your browser")
        print("2. Create a file called 'auth_code.txt' in this directory")
        print("3. Paste the code into that file and save it")
        print("4. Press Enter here to continue")
        print()
        
        input("Press Enter when you've saved the code to auth_code.txt: ")
        
        # Read the code from file
        try:
            if not os.path.exists('auth_code.txt'):
                print("❌ File 'auth_code.txt' not found")
                print("Please create the file and paste your authorization code into it")
                return False
            
            with open('auth_code.txt', 'r') as f:
                auth_code = f.read().strip()
            
            print(f"📝 Read code from file (length: {len(auth_code)} characters)")
            
            if len(auth_code) < 10:
                print("⚠️  Code seems too short, make sure you copied the full code")
                return False
            
            print(f"🔍 Code starts with: {auth_code[:30]}...")
            
            # Clean up the code (remove any extra parameters)
            if '&' in auth_code:
                original_length = len(auth_code)
                auth_code = auth_code.split('&')[0]
                print(f"🧹 Cleaned code (was {original_length}, now {len(auth_code)} chars)")
            
            # Clean up the file
            os.remove('auth_code.txt')
            print("🗑️  Removed temporary auth_code.txt file")
            
            # Exchange authorization code for tokens
            return self._exchange_code_for_tokens(auth_code)
            
        except Exception as e:
            print(f"❌ Error reading auth code file: {e}")
            return False
    
    def _exchange_code_for_tokens(self, auth_code):
        """
        Exchange authorization code for access and refresh tokens
        """
        print("🔄 Exchanging authorization code for tokens...")
        print(f"📝 Using auth code: {auth_code[:10]}...")  # Show first 10 chars for debugging
        
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }
        
        try:
            print("🌐 Making token request...")
            response = requests.post(self.token_url, data=token_data)
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Token request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            token_response = response.json()
            print("✅ Token response received")
            
            if self._save_tokens(token_response):
                return True
            else:
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to exchange code for tokens: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def _refresh_access_token(self):
        """
        Refresh the access token using refresh token
        """
        if not self.refresh_token:
            return False
        
        refresh_data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }
        
        try:
            response = requests.post(self.token_url, data=refresh_data)
            response.raise_for_status()
            
            token_response = response.json()
            return self._save_tokens(token_response)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to refresh token: {e}")
            return False
    
    def get_headers(self):
        """
        Get headers for API requests
        """
        if not self.access_token:
            return None
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'X-API-Key': self.client_id,
            'Content-Type': 'application/json'
        }

    def _strip_adobe_prefix(self, raw_response_text):
        """Strips the 'while (1) {}' prefix from Adobe API responses."""
        if raw_response_text.startswith('while (1) {}'):
            return raw_response_text[12:]
        return raw_response_text

    def make_authenticated_request(self, method, endpoint, headers=None, json_data=None, data=None, stream=False, params=None, base_url=None):
        """
        Makes an authenticated request to the Adobe Lightroom API.
        """
        if not self.access_token:
            raise requests.exceptions.RequestException("No access token available for Adobe API request.")

        target_base = base_url if base_url else self.api_base
        url = f"{target_base}{endpoint}" 

        combined_headers = self.get_headers()
        if headers:
            combined_headers.update(headers) 

        # --- ADD THESE DEBUG PRINTS ---
        # console.print(f"\n[bold yellow]--- Debugging Adobe API Request ---[/bold yellow]")
        # console.print(f"[bold yellow]Method:[/bold yellow] {method}")
        # console.print(f"[bold yellow]URL:[/bold yellow] {url}")
        # console.print(f"[bold yellow]Headers being sent:[/bold yellow]")
        # for key, value in combined_headers.items():
        #     if key.lower() == 'authorization':
        #         # Only print part of the token for security
        #         console.print(f"  [cyan]{key}[/cyan]: [dim]{value[:30]}...{value[-10:]}[/dim]")
        #     else:
        #         console.print(f"  [cyan]{key}[/cyan]: [dim]{value}[/dim]")
        # if json_data:
        #     console.print(f"[bold yellow]JSON Data:[/bold yellow] {json.dumps(json_data, indent=2)}")
        # console.print(f"[bold yellow]---------------------------------[/bold yellow]\n")
        # --- END DEBUG PRINTS ---

        try:
            response = requests.request(
                method,
                url,
                headers=combined_headers,
                json=json_data,
                data=data,
                stream=stream,
                params=params
            )
            response.raise_for_status() 

            if 'application/json' in response.headers.get('Content-Type', '') and not stream:
                response._content = self._strip_adobe_prefix(response.text).encode('utf-8')

            return response
        except requests.exceptions.RequestException as e:
            console.print(f"❌ Adobe API request failed ({method} {url}): {e}", style="red")
            if hasattr(e, 'response') and e.response:
                console.print(f"Response content: {e.response.text}", style="red")
            raise 

    def test_connection(self):
        """
        Test the connection by getting user info
        """
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        headers = self.get_headers()
        if not headers:
            return False
        
        try:
            print("🧪 Testing Adobe Lightroom API connection...")

            # Test with a simple API call to get account info
            response = requests.get(f"{self.api_base}/v2/account", headers=headers)
            
            print(f"📊 API Response status: {response.status_code}")
            
            if response.status_code == 200:
                raw_response = response.text
                
                # Adobe prefixes responses with "while (1) {}" for security
                # We need to strip this before parsing JSON
                if raw_response.startswith('while (1) {}'):
                    json_response = raw_response[12:]  # Remove "while (1) {}"
                    print("🧹 Stripped Adobe security prefix")
                else:
                    json_response = raw_response
                
                try:
                    account_info = json.loads(json_response)
                    self.account_info = account_info
                    print(f"👤 Connected to Adobe Lightroom")
                    print(f"   Account ID: {account_info.get('id', 'Unknown')}")
                    print(f"   Email: {account_info.get('email', 'Unknown')}")
                    print(f"   Name: {account_info.get('full_name', 'Unknown')}")
                    print(f"   Type: {account_info.get('type', 'Unknown')}")
                    return True
                except json.JSONDecodeError as e:
                    print(f"❌ Still invalid JSON after cleanup: {e}")
                    print(f"Cleaned response: {json_response[:200]}...")
                    return False
            else:
                print(f"❌ API request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection test failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during connection test: {e}")
            return False

def main():
    """
    Test function - run this file directly to test authentication
    """
    print("🧪 Testing Adobe Lightroom authentication...")
    auth = AdobeLightroomAuth()
    
    if auth.authenticate():
        auth.test_connection()
    else:
        print("❌ Authentication failed")

if __name__ == "__main__":
    main()