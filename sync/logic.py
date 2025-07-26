import io
import json
import uuid
import requests
from datetime import datetime
from rich.console import Console
from googleapiclient.http import MediaIoBaseDownload 

console = Console()

class SyncLogic:
    def __init__(self, google_drive_auth, adobe_lightroom_auth):
        self.google_drive_auth = google_drive_auth
        self.adobe_lightroom_auth = adobe_lightroom_auth

    def list_drive_files(self, folder_id):
        """
        Lists all files within a specified Google Drive folder using the Google Drive API.
        """
        console.print(f"\n📂 [bold blue]Listing files in Google Drive folder ID:[/bold blue] {folder_id}")
        
        try:
            results = self.google_drive_auth.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType, size)"
            ).execute()
            files = results.get('files', [])
            
            if not files:
                console.print("    No files found in this Google Drive folder.")
            else:
                console.print(f"    Found [bold]{len(files)}[/bold] files:")
                for file in files:
                    console.print(f"    - Name: [cyan]{file.get('name')}[/cyan], ID: [grey50]{file.get('id')}[/grey50], Type: {file.get('mimeType')}")
            
            return files

        except Exception as e:
            console.print(f"❌ Error listing Google Drive files: [red]{e}[/red]", style="red")
            return []

    def _download_file_from_drive(self, file_id, file_name):
        """
        Downloads a file from Google Drive.
        Returns the file content as bytes.
        """
        console.print(f"    ⬇️ [dim]Downloading '{file_name}' from Google Drive...[/dim]")
        try:
            request = self.google_drive_auth.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.seek(0)
            console.print(f"    ✅ [dim]Downloaded '{file_name}'.[/dim]")
            return fh.read()
        except Exception as e:
            console.print(f"    ❌ [red]Error downloading '{file_name}': {e}[/red]")
            return None

    def _get_asset_subtype(self, mime_type):
        """
        Determine the asset subtype based on MIME type
        """
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        else:
            return 'image'  # Default to image

    def _upload_file_to_lightroom(self, catalogue_id, file_content, file_name, album_id, mime_type="image/jpeg"):
        """
        Upload file content to Lightroom using the correct Adobe API workflow.
        
        FIXED: Uses the proper 2-step Adobe Lightroom upload process:
        1. Create asset with PUT /v2/catalogs/{catalog_id}/assets/{asset_id}
        2. Upload binary data with PUT /v2/catalogs/{catalog_id}/assets/{asset_id}/master
        """
        if not file_content:
            console.print(f"        ⚠️ [yellow]Skipping upload for '{file_name}' due to missing content.[/yellow]")
            return False

        console.print(f"        ⬆️ [dim]Uploading '{file_name}' to Lightroom album ID '{album_id}'...[/dim]")
        
        try:
            # Generate a unique asset ID (GUID without hyphens as per Adobe docs)
            asset_id = str(uuid.uuid4()).replace('-', '')
            console.print(f"        [dim]Generated asset ID: {asset_id}[/dim]")
            
            # Step 1: Create an Asset
            create_asset_endpoint = f"/v2/catalogs/{catalogue_id}/assets/{asset_id}"
            
            # Determine asset subtype
            asset_subtype = self._get_asset_subtype(mime_type)
            
            create_payload = {
                "subtype": asset_subtype,
                "payload": {
                    "captureDate": datetime.now().isoformat(),
                    "importSource": {
                        "fileName": file_name,
                        "importedOnDevice": "Partner API Upload",
                        "importedBy": self.adobe_lightroom_auth.account_info.get('id', 'Unknown'),
                        "importTimestamp": datetime.now().isoformat()
                    }
                }
            }
            
            console.print(f"        [dim]1/3: Creating asset '{file_name}' with ID {asset_id}...")
            response = self.adobe_lightroom_auth.make_authenticated_request(
                method="PUT",
                endpoint=create_asset_endpoint,
                json_data=create_payload,
                headers={
                    'Content-Type': 'application/json',
                    'If-None-Match': '*'  # Ensures we don't overwrite existing assets
                }
            )
            
            if response.status_code not in [201, 200]:
                raise ValueError(f"Asset creation failed with status {response.status_code}")
            
            console.print(f"        [dim]Asset created successfully.[/dim]")

            # Step 2: Upload the Binary Data
            upload_master_endpoint = f"/v2/catalogs/{catalogue_id}/assets/{asset_id}/master"
            
            console.print(f"        [dim]2/3: Uploading binary data for '{file_name}'...")
            
            # Upload headers for binary data
            upload_headers = {
                'Content-Type': mime_type,
                'Content-Length': str(len(file_content))
            }
            
            # Remove the default JSON content-type and use binary upload
            response = self.adobe_lightroom_auth.make_authenticated_request(
                method="PUT",
                endpoint=upload_master_endpoint,
                data=file_content,  # Use 'data' for binary, not 'json_data'
                headers=upload_headers
            )
            
            if response.status_code not in [201, 200]:
                raise ValueError(f"Binary upload failed with status {response.status_code}")
            
            console.print(f"        [dim]Binary data uploaded successfully.[/dim]")

            # Step 3: Add the asset to the Album
            add_to_album_endpoint = f"/v2/catalogs/{catalogue_id}/albums/{album_id}/assets"
            
            add_payload = {
                "resources": [
                    {
                        "id": asset_id,
                        "payload": {
                            "cover": False
                        }
                    }
                ]
            }
            
            console.print(f"        [dim]3/3: Adding asset '{file_name}' to album '{album_id}'...")
            response = self.adobe_lightroom_auth.make_authenticated_request(
                method="PUT",
                endpoint=add_to_album_endpoint,
                json_data=add_payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code not in [201, 200]:
                console.print(f"        ⚠️ [yellow]Warning: Could not add to album (status {response.status_code}), but upload succeeded.[/yellow]")
            else:
                console.print(f"        [dim]Asset added to album successfully.[/dim]")
            
            console.print(f"        ✅ [green]Successfully uploaded '{file_name}' to Lightroom.[/green]")
            return True

        except requests.exceptions.HTTPError as http_err:
            console.print(f"        ❌ [red]HTTP Error uploading '{file_name}': {http_err}[/red]")
            if http_err.response is not None:
                console.print(f"           [red]Response: {http_err.response.text}[/red]")
            return False
        except Exception as e:
            console.print(f"        ❌ [red]General Error uploading '{file_name}': {e}[/red]")
            return False

    def sync_folder_to_album(self, drive_files, album_id, album_name, catalogue_id):
        """
        Downloads files from Google Drive and uploads them to a Lightroom album in batches.
        """
        if not drive_files:
            console.print("\n⏩ [bold yellow]No files to synchronize.[/bold yellow]")
            return

        console.print(f"\n🔄 [bold purple]Starting actual synchronization of files to album:[/bold purple] [bold]{album_name}[/bold]")
        
        batch_size = 5
        for i in range(0, len(drive_files), batch_size):
            batch = drive_files[i:i + batch_size]
            console.print(f"\n    [bold cyan]Processing batch {int(i/batch_size) + 1} of {len(drive_files) // batch_size + (1 if len(drive_files) % batch_size > 0 else 0)}:[/bold cyan]")
            for file in batch:
                file_name = file.get('name', 'Unknown File')
                file_id = file.get('id')
                file_mime_type = file.get('mimeType', 'application/octet-stream')

                if not file_id:
                    console.print(f"        ⚠️ [yellow]Skipping '{file_name}' - no file ID found.[/yellow]")
                    continue

                file_content = self._download_file_from_drive(file_id, file_name)
                if file_content:
                    self._upload_file_to_lightroom(catalogue_id, file_content, file_name, album_id, file_mime_type)
                else:
                    console.print(f"        ❌ [red]Failed to get content for '{file_name}', skipping upload.[/red]")
        
        console.print("\n✅ [bold green]Synchronization process complete![/bold green]")