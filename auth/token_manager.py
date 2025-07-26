#!/usr/bin/env python3
"""
Token Manager
Centralized token storage and management for all services
"""

import os
import json
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self):
        self.tokens_dir = 'tokens'
        self.config_file = 'config.json'
        
        # Create tokens directory if it doesn't exist
        os.makedirs(self.tokens_dir, exist_ok=True)
    
    def save_config(self, service, config_data):
        """
        Save configuration data for a service
        """
        config = self.load_config()
        config[service] = config_data
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"💾 Saved configuration for {service}")
    
    def load_config(self):
        """
        Load configuration data
        """
        if not os.path.exists(self.config_file):
            return {}
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load config: {e}")
            return {}
    
    def get_config(self, service):
        """
        Get configuration for a specific service
        """
        config = self.load_config()
        return config.get(service, {})
    
    def is_authenticated(self, service):
        """
        Check if we have valid authentication for a service
        """
        if service == 'google':
            return os.path.exists(f'{self.tokens_dir}/google_token.pickle')
        elif service == 'adobe':
            token_file = f'{self.tokens_dir}/adobe_token.json'
            if not os.path.exists(token_file):
                return False
            
            # Check if Adobe token is still valid
            try:
                with open(token_file, 'r') as f:
                    token_data = json.load(f)
                
                expires_at_str = token_data.get('expires_at')
                if expires_at_str:
                    from datetime import datetime, timedelta
                    expires_at = datetime.fromisoformat(expires_at_str)
                    # Consider valid if expires more than 5 minutes from now
                    return datetime.now() < (expires_at - timedelta(minutes=5))
                
                return False
            except:
                return False
        return False
    
    def clear_tokens(self, service=None):
        """
        Clear tokens for a service (or all if service is None)
        """
        if service:
            files_to_remove = []
            if service == 'google':
                files_to_remove.append(f'{self.tokens_dir}/google_token.pickle')
            elif service == 'adobe':  
                files_to_remove.append(f'{self.tokens_dir}/adobe_token.json')
        else:
            # Clear all tokens
            files_to_remove = [
                f'{self.tokens_dir}/google_token.pickle',
                f'{self.tokens_dir}/adobe_token.json'
            ]
        
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  Removed {file_path}")
    
    def get_auth_status(self):
        """
        Get authentication status for all services
        """
        status = {
            'google': self.is_authenticated('google'),
            'adobe': self.is_authenticated('adobe')
        }
        
        return status
    
    def print_status(self):
        """
        Print current authentication status
        """
        print("\n📊 Authentication Status:")
        print("=" * 30)
        
        status = self.get_auth_status()
        
        for service, authenticated in status.items():
            icon = "✅" if authenticated else "❌"
            service_name = service.title()
            print(f"{icon} {service_name}: {'Authenticated' if authenticated else 'Not authenticated'}")
        
        print("=" * 30)

def main():
    """
    Test function
    """
    print("🧪 Testing Token Manager...")
    manager = TokenManager()
    manager.print_status()

if __name__ == "__main__":
    main()