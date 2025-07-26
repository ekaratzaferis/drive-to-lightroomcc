#!/usr/bin/env python3
"""
Lightroom Sync Tool
Complete flow: Authentication -> Folder Selection -> Album Selection -> Summary
"""

from auth.google_auth import GoogleDriveAuth
from auth.adobe_auth import AdobeLightroomAuth
from auth.token_manager import TokenManager
from ui.menus import GoogleDriveFolderSelector, LightroomAlbumSelector
from rich.console import Console
from sync.logic import SyncLogic

console = Console()

def main():
    console.print("🚀 [bold blue]Lightroom Sync Tool[/bold blue]")
    console.print("=" * 50)
    
    # Step 1: Authentication
    console.print("\n📋 [bold]Step 1: Authentication[/bold]")
    
    # Initialize token manager
    token_manager = TokenManager()
    token_manager.print_status()
    
    # Authenticate with Google Drive
    google_auth = GoogleDriveAuth()
    
    if not google_auth.authenticate():
        console.print("❌ Google Drive authentication failed", style="red")
        return
    
    google_auth.test_connection()
    
    # Authenticate with Adobe Lightroom
    adobe_auth = AdobeLightroomAuth()
    
    if not adobe_auth.authenticate():
        console.print("❌ Adobe Lightroom authentication failed", style="red")
        return
    
    adobe_auth.test_connection()
    
    console.print("\n✅ [bold green]Authentication complete![/bold green]")
    
    # Step 2: Google Drive Folder Selection
    console.print("\n📋 [bold]Step 2: Select Google Drive Folder[/bold]")
    
    folder_selector = GoogleDriveFolderSelector(google_auth)
    folder_id, folder_path = folder_selector.select_folder()
    
    if not folder_id:
        console.print("❌ No folder selected, exiting", style="red")
        return
    
    # Step 3: Lightroom Album Selection
    console.print("\n📋 [bold]Step 3: Select Lightroom Album[/bold]")
    
    album_selector = LightroomAlbumSelector(adobe_auth)
    album_id, album_name, catalogue_id = album_selector.select_album()
    
    if not album_id:
        console.print("❌ No album selected, exiting", style="red")
        return
    
    # Step 4: Display Selections Summary
    console.print("\n📋 [bold]Step 4: Configuration Summary[/bold]")
    console.print("\n" + "=" * 60)
    console.print("🎯 [bold green]SYNC CONFIGURATION[/bold green]")
    console.print("=" * 60)
    console.print(f"📂 [bold]Source (Google Drive):[/bold] {folder_path}")
    console.print(f"🎨 [bold]Destination (Lightroom):[/bold] {album_name}")
    console.print(f"🔗 [bold]Folder ID:[/bold] {folder_id}")
    console.print(f"🔗 [bold]Album ID:[/bold] {album_id}")
    console.print("=" * 60)
    
    console.print("\n✅ [bold green]Setup complete! Ready for file sync.[/bold green]")
    console.print("💡 [italic]Next: We'll add the file transfer functionality.[/italic]")

     # --- Step 5: File Synchronization ---
    console.print("\n📋 [bold]Step 5: Initiating File Synchronization[/bold]")
    sync_tool = SyncLogic(google_auth, adobe_auth)
    
    # List files from Google Drive
    drive_files = sync_tool.list_drive_files(folder_id)
    
    # Perform the actual synchronization
    sync_tool.sync_folder_to_album(drive_files, album_id, album_name, catalogue_id) 
    # --- End Step ---

if __name__ == "__main__":
    main()