"""
Google Drive Integration for OOA TLEP Compliance Review System
Accesses Google Drive folders, downloads supported TLEP files (preserving folder structure),
and triggers the institutional review pipeline.
"""

import os
import re
import tempfile
from typing import List, Dict, Any, Optional, Tuple
import requests

try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    GOOGLE_API_CLIENT_AVAILABLE = True
except ImportError:
    GOOGLE_API_CLIENT_AVAILABLE = False


def extract_folder_id_from_url(url: str) -> Optional[str]:
    """Extracts Google Drive folder ID from various URL formats."""
    patterns = [
        r"drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)",
        r"drive\.google\.com/folderview\?id=([a-zA-Z0-9_-]+)",
        r"^([a-zA-Z0-9_-]{25,})$"  # Raw ID
    ]
    for p in patterns:
        m = re.search(p, url.strip())
        if m:
            return m.group(1)
    return None


class GoogleDriveConnector:
    """Manages connection and file download from Google Drive."""
    
    def __init__(self, service_account_json_path: Optional[str] = None, api_key: Optional[str] = None):
        self.service_account_path = service_account_json_path
        self.api_key = api_key
        self.service = None
        
        if GOOGLE_API_CLIENT_AVAILABLE and service_account_json_path and os.path.exists(service_account_json_path):
            creds = service_account.Credentials.from_service_account_file(
                service_account_json_path,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            self.service = build('drive', 'v3', credentials=creds)
        elif GOOGLE_API_CLIENT_AVAILABLE and api_key:
            self.service = build('drive', 'v3', developerKey=api_key)

    def list_folder_files(
        self,
        folder_id: str,
        include_subfolders: bool = True
    ) -> List[Dict[str, Any]]:
        """Lists all supported TLEP files inside a Google Drive folder."""
        if not self.service:
            # If no API service configured, attempt public directory query via Google API key or raise helpful guidance
            raise PermissionError(
                "Google Drive API credentials required to query folder. "
                "Provide a Service Account JSON or Google Drive API Key in Settings."
            )
            
        supported_extensions = ('.xlsx', '.xls', '.docx', '.pdf')
        all_files = []
        
        def _scan_folder(current_folder_id: str, current_path: str):
            query = f"'{current_folder_id}' in parents and trashed = false"
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                for item in items:
                    name = item['name']
                    mime = item['mimeType']
                    
                    if mime == 'application/vnd.google-apps.folder':
                        if include_subfolders:
                            _scan_folder(item['id'], os.path.join(current_path, name))
                    else:
                        ext = os.path.splitext(name)[1].lower()
                        if ext in supported_extensions and not name.startswith("~$"):
                            all_files.append({
                                "id": item['id'],
                                "name": name,
                                "rel_path": os.path.join(current_path, name),
                                "mimeType": mime,
                                "size": item.get('size', 0)
                            })
                            
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
        _scan_folder(folder_id, "")
        return all_files

    def download_file(self, file_id: str, destination_path: str):
        """Downloads a specific file from Google Drive."""
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        request = self.service.files().get_media(fileId=file_id)
        with open(destination_path, "wb") as f:
            f.write(request.execute())
            
    def sync_and_download_folder(
        self,
        folder_id: str,
        target_dir: str,
        include_subfolders: bool = True,
        progress_callback=None
    ) -> List[str]:
        """Downloads all supported files from Google Drive to target local directory."""
        files = self.list_folder_files(folder_id, include_subfolders=include_subfolders)
        downloaded_paths = []
        tot = len(files)
        
        for idx, f in enumerate(files, 1):
            if progress_callback:
                progress_callback(idx, tot, f['name'])
            dest = os.path.join(target_dir, f['rel_path'])
            self.download_file(f['id'], dest)
            downloaded_paths.append(dest)
            
        return downloaded_paths
