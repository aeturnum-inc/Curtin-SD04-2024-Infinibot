import requests
from typing import Dict, List, Optional
from pathlib import Path
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class SharePointAuth:
    def __init__(self):
        self.client_id = settings.SHAREPOINT_CLIENT_ID
        self.client_secret = settings.SHAREPOINT_CLIENT_SECRET
        self.tenant_id = settings.SHAREPOINT_TENANT_ID
        self._token = None

    def get_token(self) -> str:
        if not self._token:
            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default"
            }
            response = requests.post(url, data=data)
            response.raise_for_status()
            self._token = response.json()["access_token"]
        return self._token

class SharePointService:
    def __init__(self, auth_service):
        self.auth_service = auth_service

    def get_items_in_folder(self, drive_id: str, folder_id: str = "root") -> List[Dict]:
        """Fetch all items from a SharePoint folder."""
        try:
            if folder_id == "root":
                url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
            else:
                url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}/children"
                
            access_token = self.auth_service.get_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("value", [])
        except Exception as e:
            logger.error(f"Error fetching items: {str(e)}")
            return []

    def get_sharepoint_files(self, drive_id: str) -> List[Dict]:
        """Recursively fetch all files from SharePoint."""
        def recursive_file_search(items: List[Dict]) -> List[Dict]:
            all_files = []
            for item in items:
                if item.get("file"):
                    all_files.append(item)
                elif item.get("folder"):
                    folder_items = self.get_items_in_folder(drive_id, item.get("id"))
                    all_files.extend(recursive_file_search(folder_items))
            return all_files

        root_items = self.get_items_in_folder(drive_id)
        return recursive_file_search(root_items)

    def download_file(self, drive_id: str, file_id: str, temp_dir: str, original_filename: str) -> Optional[Path]:
        """Download a file from SharePoint."""
        try:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
            access_token = self.auth_service.get_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            file_extension = Path(original_filename).suffix
            file_path = Path(temp_dir) / f"{file_id}{file_extension}"
            file_path.write_bytes(response.content)
            return file_path
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return None

    def get_all_drives(self, site_id: str) -> List[Dict]:
        """Get all drives in a SharePoint site."""
        try:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
            access_token = self.auth_service.get_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("value", [])
        except Exception as e:
            logger.error(f"Error fetching drives: {str(e)}")
            return []