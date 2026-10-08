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


def parse_drive_url_type(url: str) -> Tuple[Optional[str], str]:
    """
    Parses Google Drive / Docs / Sheets URL.
    Returns (resource_id, resource_type) where resource_type is:
    'folder', 'spreadsheet', 'document', 'file', or 'unknown'.
    """
    url_clean = url.strip()
    
    # 1. Folder check
    folder_match = re.search(r"drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)", url_clean)
    if folder_match:
        return folder_match.group(1), "folder"
    if re.search(r"drive\.google\.com/folderview\?id=([a-zA-Z0-9_-]+)", url_clean):
        m = re.search(r"drive\.google\.com/folderview\?id=([a-zA-Z0-9_-]+)", url_clean)
        return m.group(1), "folder"
        
    # 2. Spreadsheet check
    sheet_match = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url_clean)
    if sheet_match:
        return sheet_match.group(1), "spreadsheet"
        
    # 3. Document check
    doc_match = re.search(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)", url_clean)
    if doc_match:
        return doc_match.group(1), "document"
        
    # 4. File check
    file_match = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", url_clean)
    if file_match:
        return file_match.group(1), "file"
        
    # 5. Raw 25+ char ID fallback (assumed folder)
    if re.match(r"^[a-zA-Z0-9_-]{25,}$", url_clean):
        return url_clean, "folder"
        
    return None, "unknown"


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
            
    def export_or_download_single_resource(self, resource_id: str, resource_type: str, dest_dir: str) -> str:
        """Downloads or exports an individual Google Drive resource (Sheet, Doc, or File)."""
        os.makedirs(dest_dir, exist_ok=True)
        
        # 1. Google Spreadsheet -> .xlsx
        if resource_type == "spreadsheet":
            dest_path = os.path.join(dest_dir, f"drive_sheet_{resource_id}.xlsx")
            if self.service:
                request = self.service.files().export_media(
                    fileId=resource_id,
                    mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                with open(dest_path, "wb") as f:
                    f.write(request.execute())
                return dest_path
            else:
                # Public export fallback
                url = f"https://docs.google.com/spreadsheets/d/{resource_id}/export?format=xlsx"
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200 and len(resp.content) > 200:
                    with open(dest_path, "wb") as f:
                        f.write(resp.content)
                    return dest_path
                raise PermissionError("Unable to export Google Sheet. Provide credentials or verify link sharing.")

        # 2. Google Doc -> .docx
        elif resource_type == "document":
            dest_path = os.path.join(dest_dir, f"drive_doc_{resource_id}.docx")
            if self.service:
                request = self.service.files().export_media(
                    fileId=resource_id,
                    mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                with open(dest_path, "wb") as f:
                    f.write(request.execute())
                return dest_path
            else:
                url = f"https://docs.google.com/document/d/{resource_id}/export?format=docx"
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200 and len(resp.content) > 200:
                    with open(dest_path, "wb") as f:
                        f.write(resp.content)
                    return dest_path
                raise PermissionError("Unable to export Google Doc. Provide credentials or verify link sharing.")

        # 3. Direct File
        else:
            dest_path = os.path.join(dest_dir, f"drive_file_{resource_id}.xlsx")
            if self.service:
                request = self.service.files().get_media(fileId=resource_id)
                with open(dest_path, "wb") as f:
                    f.write(request.execute())
                return dest_path
            else:
                url = f"https://drive.google.com/uc?export=download&id={resource_id}"
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200 and len(resp.content) > 200:
                    with open(dest_path, "wb") as f:
                        f.write(resp.content)
                    return dest_path
                raise PermissionError("Unable to download Google Drive file. Provide credentials or verify link sharing.")

    def fetch_drive_resource(
        self,
        url_or_id: str,
        target_dir: str,
        include_subfolders: bool = True,
        progress_callback = None
    ) -> Tuple[str, List[str]]:
        """
        Intelligently resolves Google Drive URL or ID (folder vs spreadsheet vs doc vs file).
        Returns (resource_type, downloaded_file_paths).
        """
        r_id, r_type = parse_drive_url_type(url_or_id)
        if not r_id:
            raise ValueError(f"Could not parse valid Google Drive ID from: {url_or_id}")

        if r_type == "folder":
            downloaded = self.sync_and_download_folder(
                folder_id=r_id,
                target_dir=target_dir,
                include_subfolders=include_subfolders,
                progress_callback=progress_callback
            )
            return ("folder", downloaded)
        else:
            single_path = self.export_or_download_single_resource(
                resource_id=r_id,
                resource_type=r_type,
                dest_dir=target_dir
            )
            return (r_type, [single_path])
