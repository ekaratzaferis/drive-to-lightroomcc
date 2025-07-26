#!/usr/bin/env python3
"""
Interactive Selection Menus
Handles folder and album selection with rich UI (Python 3.13 compatible)
"""

import json
import requests
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt


console = Console()

class GoogleDriveFolderSelector:
    def __init__(self, google_auth):
        self.google_auth = google_auth
        self.service = google_auth.get_service()
    
    def list_folders(self, parent_id='root', max_results=50):
        """
        List folders in Google Drive
        """
        try:
            # Query for folders only
            query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, parents, modifiedTime)"
            ).execute()
            
            folders = results.get('files', [])
            return folders
            
        except Exception as e:
            console.print(f"❌ Error listing folders: {e}", style="red")
            return []
    
    def get_folder_path(self, folder_id):
        """
        Get the full path of a folder
        """
        try:
            if folder_id == 'root':
                return "📁 My Drive"
            
            # Get folder info
            folder = self.service.files().get(fileId=folder_id, fields="name, parents").execute()
            folder_name = folder.get('name', 'Unknown')
            
            # Get parent path recursively
            parents = folder.get('parents', [])
            if parents and parents[0] != 'root':
                parent_path = self.get_folder_path(parents[0])
                return f"{parent_path} / {folder_name}"
            else:
                return f"📁 My Drive / {folder_name}"
                
        except Exception as e:
            return f"📁 Unknown Path ({folder_id})"
    
    def select_folder(self):
        """
        Interactive folder selection
        """
        console.print("\n🔍 [bold blue]Google Drive Folder Selection[/bold blue]")
        console.print("=" * 50)
        
        current_folder_id = 'root'
        current_path = "📁 My Drive"
        
        while True:
            console.print(f"\n📍 Current location: [bold]{current_path}[/bold]")
            
            # Load folders with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Loading folders...", total=None)
                folders = self.list_folders(current_folder_id)
                progress.remove_task(task)
            
            # Prepare options
            options = []
            
            # Add option to select current folder (if not root)
            if current_folder_id != 'root':
                options.append(("select", "✅ Select this folder", None))
            
            # Add option to go back (if not root)
            if current_folder_id != 'root':
                options.append(("back", "⬅️  Go back to parent folder", None))
            
            # Add folders
            for i, folder in enumerate(folders):
                folder_name = folder.get('name', 'Unknown')
                options.append(("folder", f"📁 {folder_name}", folder))
            
            if not options:
                console.print("📂 No folders found")
                if current_folder_id == 'root':
                    console.print("❌ No folders found in your Google Drive")
                    return None, None
                else:
                    console.print("You can select this folder or go back")
                    options.append(("select", "✅ Select this folder", None))
                    options.append(("back", "⬅️  Go back to parent folder", None))
            
            # Display options
            console.print("\n[bold]Options:[/bold]")
            for i, (action, description, data) in enumerate(options, 1):
                console.print(f"  {i}. {description}")
            
            # Get user choice
            while True:
                try:
                    choice = Prompt.ask(
                        "\n[bold]Choose an option[/bold]",
                        choices=[str(i) for i in range(1, len(options) + 1)],
                        default="1"
                    )
                    choice_idx = int(choice) - 1
                    break
                except (ValueError, IndexError):
                    console.print("❌ Invalid choice, please try again", style="red")
            
            action, description, data = options[choice_idx]
            
            if action == "select":
                # User selected current folder
                console.print(f"\n✅ [bold green]Selected folder:[/bold green] {current_path}")
                return current_folder_id, current_path
            
            elif action == "back":
                # Go back to parent
                if current_folder_id != 'root':
                    try:
                        folder = self.service.files().get(fileId=current_folder_id, fields="parents").execute()
                        parents = folder.get('parents', [])
                        if parents:
                            current_folder_id = parents[0]
                            current_path = self.get_folder_path(current_folder_id)
                        else:
                            current_folder_id = 'root'
                            current_path = "📁 My Drive"
                    except:
                        current_folder_id = 'root'
                        current_path = "📁 My Drive"
            
            elif action == "folder":
                # User selected a subfolder
                current_folder_id = data['id']
                current_path = self.get_folder_path(current_folder_id)

class LightroomAlbumSelector:
    def __init__(self, adobe_auth):
        self.adobe_auth = adobe_auth
        self.api_base = "https://lr.adobe.io"
        self.headers = self.adobe_auth.get_headers() 
        self.catalog_id = None
        self.display_page_size = 25 # How many albums to display per screen

    def _parse_adobe_response(self, response_text):
        """
        Parse Adobe's response, removing the security prefix
        """
        if response_text.startswith('while (1) {}'):
            return json.loads(response_text[12:])
        return json.loads(response_text)
    
    def get_catalog_id(self):
        """
        Step 1: Get the user's catalog ID (required for all other calls)
        """
        # Ensure headers are up-to-date here too in case of stale token
        self.headers = self.adobe_auth.get_headers() 
        console.print("🔍 Getting user catalog...")
        
        try:
            response = requests.get(f"{self.api_base}/v2/catalog", headers=self.headers)
            
            console.print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = self._parse_adobe_response(response.text)
                
                if 'id' in data:
                    self.catalog_id = data['id']
                    console.print(f"   ✅ Catalog ID: {self.catalog_id}")
                    return True
                else:
                    console.print(f"   ❌ No catalog ID found in response: {list(data.keys())}")
                    return False
                    
            elif response.status_code == 401:
                console.print("   🔐 Authentication failed - check your tokens")
                return False
            elif response.status_code == 403:
                console.print("   🚫 Access denied - check your API permissions")
                return False
            else:
                console.print(f"   ❌ Error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            console.print(f"   💥 Exception: {e}")
            return False
    
    def list_albums(self, limit=None, offset=0, next_link=None):
        """
        Step 2: List albums using the catalog ID with pagination
        Returns (albums_list_for_current_fetch, next_page_link_or_None)
        
        If next_link is provided, it takes precedence over limit and offset.
        """
        if not self.catalog_id:
            console.print("❌ No catalog ID - call get_catalog_id() first")
            return [], None 
        
        try:
            url = next_link if next_link else f"{self.api_base}/v2/catalogs/{self.catalog_id}/albums"
            
            params = {}
            # Only apply limit and offset if a direct next_link is NOT being used
            if not next_link: 
                if limit is not None:
                    params['limit'] = limit
                if offset > 0:
                    params['offset'] = offset
            
            console.print(f"🎨 Fetching albums from: {url} with params: {params}")
            
            response = requests.get(url, headers=self.headers, params=params)
            console.print(f"   Status: {response.status_code}")
            
            albums = []
            next_page_link = None 

            if response.status_code == 200:
                data = self._parse_adobe_response(response.text)
                
                # Check for pagination link
                if 'links' in data and 'next' in data['links']:
                    next_link_href = data['links']['next']['href']
                    if next_link_href: # Ensure href exists
                        next_page_link = f"{self.api_base}/v2/catalogs/{self.catalog_id}/{next_link_href}"
                    console.print(f"   ➡️ Next page link in response: {next_page_link}")
                
                if 'resources' in data and isinstance(data['resources'], list):
                    console.print(f"   🎯 Found {len(data['resources'])} albums in 'resources' for current fetch")
                    for album_data in data['resources']:
                        album = self._extract_album_info(album_data)
                        if album['id']:
                            albums.append(album)
                else:
                    console.print(f"   ⚠️  Unexpected response structure for albums: {json.dumps(data, indent=2)[:500]}...")
                
                return albums, next_page_link
                
            elif response.status_code == 404:
                console.print("   📭 Catalog not found - catalog_id might be invalid")
                return [], None
            elif response.status_code == 401:
                console.print("   🔐 Authentication failed")
                return [], None
            elif response.status_code == 403:
                console.print("   🚫 Access denied")
                return [], None
            else:
                console.print(f"   ❌ Error {response.status_code}: {response.text[:200]}")
                return [], None
                
        except Exception as e:
            console.print(f"   💥 Exception: {e}")
            return [], None
    
    def _extract_album_info(self, album_data):
        """
        Extract album information from the API response
        """
        album_info = {
            'id': None,
            'name': 'Unnamed Album',
            'created': None,
            'updated': None,
            'subtype': None
        }
        
        if 'id' in album_data:
            album_info['id'] = album_data['id']
        
        if 'payload' in album_data and isinstance(album_data['payload'], dict):
            payload = album_data['payload']
            
            if 'name' in payload:
                album_info['name'] = payload['name']
            
            if 'subtype' in payload:
                album_info['subtype'] = payload['subtype']
        
        if 'created' in album_data:
            album_info['created'] = album_data['created']
        if 'updated' in album_data:
            album_info['updated'] = album_data['updated']
        
        return album_info
    
    def select_album(self):
        """
        Interactive album selection with pagination.
        This method now fully manages the pagination logic to ensure correct display and fetching.
        """
        console.print("\n🎨 [bold blue]Lightroom Album Selection[/bold blue]")
        console.print("=" * 60)
        
        # Step 1: Get catalog ID
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Getting catalog information...", total=None)
            
            if not self.get_catalog_id():
                progress.remove_task(task)
                console.print("❌ Failed to get catalog ID")
                return None, None
            
            progress.remove_task(task) 

        # This list will hold only the albums for the currently displayed page
        current_page_albums = [] 
        # This variable will hold the 'next' URL provided by the Adobe API for the next fetch
        next_api_url = None 
        # This stack will store (offset, next_url) tuples for previously viewed pages to go back
        previous_page_states = [] 
        # This tracks the current API offset for the page being viewed
        current_api_offset = 0 

        # --- Initial Load of the first page of albums from API ---
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading initial albums...", total=None)
            
            # Fetch the first batch of albums using offset 0 and the display_page_size
            fetched_albums, fetched_next_link = self.list_albums(
                limit=self.display_page_size, # Request exactly the display page size
                offset=current_api_offset 
            )
            
            if not fetched_albums:
                progress.remove_task(task)
                console.print("📱 No albums found in your Lightroom CC catalog")
                console.print("💡 Make sure you have albums created in Lightroom CC")
                return None, None

            current_page_albums = fetched_albums
            next_api_url = fetched_next_link
            progress.remove_task(task)

        # --- Interactive Display and Selection Loop ---
        while True:
            num_albums_on_current_page = len(current_page_albums)
            
            # Display the albums in a Rich Table
            # The title now reflects the current offset and count on the page
            table = Table(
                title=f"Albums in Catalog: {self.catalog_id} "
                      f"(Displaying {current_api_offset + 1}-{current_api_offset + num_albums_on_current_page})"
            )
            table.add_column("#", style="bold", width=4)
            table.add_column("Album Name", style="cyan")
            table.add_column("Type", style="yellow", width=12)
            table.add_column("Created", style="magenta", width=12)
            table.add_column("Updated", style="green", width=12)
            
            for i, album in enumerate(current_page_albums):
                # Numbering from 1 for the current page
                display_index = i + 1 
                created = album.get('created', 'Unknown')[:10] if album.get('created') else 'Unknown'
                updated = album.get('updated', 'Unknown')[:10] if album.get('updated') else 'Unknown'
                subtype = album.get('subtype', 'album')
                
                table.add_row(str(display_index), album['name'], subtype, created, updated)
            
            console.print(table)
            
            # Prepare valid choices for the user prompt
            valid_choices = []
            
            # 'p' (previous) is an option if there are previous page states in the stack
            if previous_page_states:
                valid_choices.append("p")
            
            # 'n' (next) is an option if there's a next API URL
            if next_api_url:
                valid_choices.append("n")
            
            # Allow selecting any album by its number on the current page
            valid_choices.extend([str(i) for i in range(1, num_albums_on_current_page + 1)]) 

            # Construct the prompt message dynamically
            prompt_message = "\n[bold]Select an album (enter #)"
            if "p" in valid_choices: prompt_message += " or (p)revious"
            if "n" in valid_choices: prompt_message += " or (n)ext"
            prompt_message += "[/bold]"
            
            user_input = Prompt.ask(prompt_message, choices=valid_choices).lower()
            
            if user_input == 'p':
                if previous_page_states:
                    # Pop the last state from the stack to go back
                    prev_offset, prev_next_url = previous_page_states.pop()
                    current_api_offset = prev_offset
                    next_api_url = prev_next_url # Restore the next URL for this previous page
                    
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(f"Loading previous albums...", total=None)
                        # Fetch the previous page using the saved offset
                        fetched_albums, _ = self.list_albums( # We don't need the next link from this call, as we already have it
                            limit=self.display_page_size, 
                            offset=current_api_offset
                        )
                        current_page_albums = fetched_albums
                        progress.remove_task(task)
                else:
                    console.print("   No previous page.", style="yellow")
            elif user_input == 'n':
                if next_api_url:
                    # Save the current page's state (offset and its next_api_url) before moving to the next page
                    previous_page_states.append((current_api_offset, next_api_url))
                    
                    # Update current_api_offset for the next page (even if using next_link, for tracking)
                    current_api_offset += self.display_page_size 

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(f"Loading next albums...", total=None)
                        
                        # Call list_albums using the stored next_api_url
                        fetched_albums, fetched_next_link = self.list_albums(
                            next_link=next_api_url # Use the direct next link for the API call
                        )
                        
                        current_page_albums = fetched_albums
                        next_api_url = fetched_next_link # Update next_api_url for the newly fetched page
                        
                        progress.remove_task(task)
                else:
                    console.print("   No more albums to display or fetch.", style="yellow")
            else:
                # User entered a number to select an album
                try:
                    # Convert to 0-based index for list access
                    choice_idx = int(user_input) - 1 
                    if 0 <= choice_idx < num_albums_on_current_page:
                        selected_album = current_page_albums[choice_idx]
                        console.print(f"\n✅ [bold green]Selected album:[/bold green] {selected_album['name']}")
                        console.print(f"   Album ID: {selected_album['id']}")
                        console.print(f"   Catalog ID: {self.catalog_id}")
                        return selected_album['id'], selected_album['name'], self.catalog_id
                    else:
                        console.print("❌ Invalid choice, please enter a valid album number or 'p'/'n'.", style="red")
                except ValueError:
                    console.print("❌ Invalid input. Please enter a number, 'p', or 'n'.", style="red")

def main():
    """
    Test function
    """
    from auth.google_auth import GoogleDriveAuth
    from auth.adobe_auth import AdobeLightroomAuth
    
    console.print("🧪 [bold]Testing Selection Menus[/bold]")
    
    # Test Google Drive folder selection
    print("\n--- Testing Google Drive Authentication ---")
    google_auth = GoogleDriveAuth()
    if google_auth.authenticate():
        folder_selector = GoogleDriveFolderSelector(google_auth)
        folder_id, folder_path = folder_selector.select_folder()
        if folder_id:
            console.print(f"Selected: {folder_path} (ID: {folder_id})")
    
    # Test Lightroom album selection
    print("\n--- Testing Adobe Lightroom Authentication ---")
    adobe_auth = AdobeLightroomAuth()
    if adobe_auth.authenticate():
        album_selector = LightroomAlbumSelector(adobe_auth)
        album_id, album_name = album_selector.select_album()
        if album_id:
            console.print(f"Selected: {album_name} (ID: {album_id})")

if __name__ == "__main__":
    main()