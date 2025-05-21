import pytest
import requests
from unittest.mock import patch, MagicMock
from app.services.sharepoint_service import SharePointService

@pytest.fixture
def service():
    return SharePointService()

def test_get_access_token_caches_token():
    service = SharePointService()
    service.access_token = "cached_token"
    # Should not call credential.get_token if token is cached
    with patch.object(service.credential, "get_token") as mock_get_token:
        token = service.get_access_token()
        assert token == "cached_token"
        mock_get_token.assert_not_called()

def test_get_access_token_fetches_token():
    service = SharePointService()
    service.access_token = None
    mock_token = MagicMock(token="new_token")
    with patch.object(service.credential, "get_token", return_value=mock_token) as mock_get_token:
        token = service.get_access_token()
        assert token == "new_token"
        mock_get_token.assert_called_once_with("https://graph.microsoft.com/.default")

def test_list_drives_raises_for_status():
    service = SharePointService()
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("fail")
        mock_get.return_value = mock_response
        with pytest.raises(requests.exceptions.HTTPError):
            service.list_drives()
        mock_get.assert_called_once()
        
def test_list_drives_returns_empty_when_no_drives(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_get.return_value = mock_response
        result = service.list_drives()
        assert result == []
        mock_get.assert_called_once()
        
def test_list_drives_handles_general_exception():
    service = SharePointService()
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get", side_effect=Exception("unexpected error")):
        with pytest.raises(Exception) as excinfo:
            service.list_drives()
        assert "unexpected error" in str(excinfo.value)

def test_get_document_content_handles_http_error(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        # First call for drives, second for document content
        mock_response_drives = MagicMock()
        mock_response_drives.raise_for_status = MagicMock()
        mock_response_drives.json.return_value = {"value": [{"id": "driveid"}]}
        mock_response_content = MagicMock()
        mock_response_content.raise_for_status.side_effect = requests.exceptions.HTTPError("fail")
        mock_get.side_effect = [mock_response_drives, mock_response_content]
        with pytest.raises(requests.exceptions.HTTPError) as excinfo:
            service.get_document_content("itemid")
        assert "fail" in str(excinfo.value)

def test_get_document_content_handles_exception(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get", side_effect=Exception("unexpected error")):
        with pytest.raises(Exception) as excinfo:
            service.get_document_content("itemid")
        assert "unexpected error" in str(excinfo.value)

def mock_drive_and_content(content_type, content=b"filecontent", extra_headers=None):
    # Helper to mock both drive and content responses
    mock_response_drives = MagicMock()
    mock_response_drives.raise_for_status = MagicMock()
    mock_response_drives.json.return_value = {"value": [{"id": "driveid"}]}
    mock_response_content = MagicMock()
    mock_response_content.raise_for_status = MagicMock()
    mock_response_content.headers = {"Content-Type": content_type}
    if extra_headers:
        mock_response_content.headers.update(extra_headers)
    mock_response_content.content = content
    mock_response_content.text = "plain text fallback"
    return [mock_response_drives, mock_response_content]

def test_get_document_content_pdf(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get, \
         patch("pdfplumber.open") as mock_pdf:
        mock_get.side_effect = mock_drive_and_content("application/pdf")
        mock_pdf.return_value.__enter__.return_value.pages = [MagicMock(extract_text=lambda: "PDF page text")]
        result = service.get_document_content("itemid")
        assert "PDF page text" in result

def test_get_document_content_docx(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get, \
         patch("docx2txt.process", return_value="docx text") as mock_docx:
        mock_get.side_effect = mock_drive_and_content("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        result = service.get_document_content("itemid")
        assert result == "docx text"
        mock_docx.assert_called_once()

def test_get_document_content_xlsx(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get, \
         patch("openpyxl.load_workbook") as mock_wb:
        mock_get.side_effect = mock_drive_and_content("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = [[1, 2, 3], [4, 5, 6]]
        mock_wb.return_value.worksheets = [mock_ws]
        result = service.get_document_content("itemid")
        assert "1 2 3" in result and "4 5 6" in result

def test_get_document_content_pptx(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get, \
         patch("app.services.sharepoint_service.Presentation") as mock_pptx:
        mock_get.side_effect = mock_drive_and_content("application/vnd.openxmlformats-officedocument.presentationml.presentation")
        # Set up the mock Presentation object
        mock_shape = MagicMock()
        mock_shape.text = "slide text"
        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        mock_pptx.return_value.slides = [mock_slide]
        result = service.get_document_content("itemid")
        assert "slide text" in result

def test_get_document_content_csv(service):
    csv_bytes = b"col1,col2\nval1,val2"
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        mock_get.side_effect = mock_drive_and_content("text/csv", content=csv_bytes)
        result = service.get_document_content("itemid")
        assert "col1, col2" in result and "val1, val2" in result

def test_get_document_content_csv_by_disposition(service):
    csv_bytes = b"col1,col2\nval1,val2"
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        mock_get.side_effect = mock_drive_and_content("application/octet-stream", content=csv_bytes, extra_headers={"Content-Disposition": "attachment; filename=file.csv"})
        result = service.get_document_content("itemid")
        assert "col1, col2" in result

def test_get_document_content_txt(service):
    txt_bytes = b"plain text file"
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        mock_get.side_effect = mock_drive_and_content("text/plain", content=txt_bytes)
        result = service.get_document_content("itemid")
        assert result == "plain text file"

def test_get_document_content_txt_by_disposition(service):
    txt_bytes = b"plain text file"
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        mock_get.side_effect = mock_drive_and_content("application/octet-stream", content=txt_bytes, extra_headers={"Content-Disposition": "attachment; filename=file.txt"})
        result = service.get_document_content("itemid")
        assert result == "plain text file"

def test_get_document_content_fallback_to_text(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get:
        mock_get.side_effect = mock_drive_and_content("application/unknown", content=b"", extra_headers={})
        result = service.get_document_content("itemid")
        assert result == "plain text fallback"

def test_get_document_content_permission_denied(service):
    with patch.object(service, "get_access_token", return_value="token"), \
         patch("requests.get") as mock_get, \
         patch.object(service, "check_user_permission", return_value=False):
        mock_get.side_effect = mock_drive_and_content("text/plain")
        with pytest.raises(Exception) as excinfo:
            service.get_document_content("itemid", user_email="user@example.com")
        assert "does not have permission" in str(excinfo.value)

#testing for webhooks
def test_get_webhook_subscriptions(service):
    with patch("requests.get") as mock_get, patch.object(service, "get_access_token", return_value="token"):
        mock_get.return_value.json.return_value = {"value": [{"id": "sub1"}]}
        mock_get.return_value.raise_for_status = lambda: None
        subs = service.get_webhook_subscriptions()
        assert subs == [{"id": "sub1"}]
        mock_get.assert_called_once()
        
def test_get_webhook_subscriptions_handles_http_error(service):
    with patch("requests.get", side_effect=requests.exceptions.RequestException("HTTP error")), \
         patch.object(service, "get_access_token", return_value="token"):
        with pytest.raises(requests.exceptions.RequestException):
            service.get_webhook_subscriptions()
        
def test_create_webhook_subscription(service):
    with patch("requests.post") as mock_post, patch.object(service, "get_access_token", return_value="token"):
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"id": "sub1"}
        # Should not raise
        service.create_webhook_subscription("resource", "http://notify.url")
        # Check that requests.post was called with expected arguments
        mock_post.assert_called_once()
        mock_post.return_value.raise_for_status.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://graph.microsoft.com/v1.0/subscriptions"
        assert kwargs["headers"]["Authorization"] == "Bearer token"
        assert kwargs["json"]["resource"] == "resource"
        assert kwargs["json"]["notificationUrl"] == "http://notify.url"

def test_create_webhook_subscription_invalid_input(service, capsys):
    # Simulate a 400 Bad Request from the API due to invalid input
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error: Bad Request for url")
    mock_response.text = '{"error": "Invalid resource or URL"}'
    with patch("requests.post", return_value=mock_response), \
         patch.object(service, "get_access_token", return_value="token"):
        with pytest.raises(requests.exceptions.HTTPError):
            # Pass invalid resource and/or URL
            service.create_webhook_subscription("", "not-a-valid-url")
        captured = capsys.readouterr()
        assert "Error creating webhook subscription: 400 Client Error: Bad Request for url" in captured.out
        assert "Response content: {\"error\": \"Invalid resource or URL\"}" in captured.out

def test_create_webhook_subscription_handles_http_error(service, capsys):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Failed to create subscription")
    with patch("requests.post", return_value=mock_response), \
         patch.object(service, "get_access_token", return_value="token"):
        with pytest.raises(requests.exceptions.RequestException):
            service.create_webhook_subscription("resource", "http://notify.url")
        captured = capsys.readouterr()
        assert "Error creating webhook subscription: Failed to create subscription" in captured.out

def test_renew_webhook_subscription(service):
    with patch("requests.patch") as mock_patch, patch.object(service, "get_access_token", return_value="token"):
        mock_patch.return_value.raise_for_status = lambda: None
        mock_patch.return_value.json.return_value = {"id": "sub1"}
        result = service.renew_webhook_subscription("sub1")
        # Check that requests.patch was called with expected arguments
        mock_patch.assert_called_once()
        args, kwargs = mock_patch.call_args
        assert args[0] == "https://graph.microsoft.com/v1.0/subscriptions/sub1"
        assert kwargs["headers"]["Authorization"] == "Bearer token"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert "expirationDateTime" in kwargs["json"]
        assert result == {"id": "sub1"}       

def test_renew_webhook_subscription_handles_http_error(service):
    with patch("requests.patch", side_effect=requests.exceptions.RequestException("Patch error")), \
         patch.object(service, "get_access_token", return_value="token"):
        with pytest.raises(requests.exceptions.RequestException):
            service.renew_webhook_subscription("sub1")

def test_delete_webhook_subscription(service):
    with patch("requests.delete") as mock_delete, patch.object(service, "get_access_token", return_value="token"):
        mock_delete.return_value.raise_for_status = lambda: None
        service.delete_webhook_subscription("sub1")
        mock_delete.assert_called_once()

def test_process_webhook_notification_handles_document_update(service):
    notification = {
        "value": [
            {
                "resource": "drives/drive-id/items/item-id",
                "changeType": "updated"
            }
        ]
    }
    with patch.object(service, 'get_access_token', return_value="token"), \
         patch.object(service, 'get_delta_link', return_value=None), \
         patch("requests.get") as mock_get, \
         patch.object(service, 'save_delta_link'), \
         patch.object(service, 'get_document_content', return_value="test content"), \
         patch.object(service, 'update_document_in_database') as mock_update_db, \
         patch.object(service, 'delete_document_from_database'):
        mock_get.return_value.json.return_value = {
            "value": [
                {
                    "@odata.type": "#microsoft.graph.driveItem",
                    "id": "item-id",
                    "name": "TestDoc.txt",
                    "webUrl": "http://example.com",
                    "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                    "parentReference": {"driveId": "drive-id"}
                }
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None
        service.process_webhook_notification(notification)
        mock_update_db.assert_called_once()

def test_process_webhook_notification_handles_folder_update(service, capsys):
    notification = {
        "value": [
            {
                "resource": "drives/drive-id/items/folder-id",
                "changeType": "updated"
            }
        ]
    }
    with patch.object(service, 'get_access_token', return_value="token"), \
         patch.object(service, 'get_delta_link', return_value=None), \
         patch("requests.get") as mock_get, \
         patch.object(service, 'save_delta_link'), \
         patch.object(service, 'get_document_content'), \
         patch.object(service, 'update_document_in_database') as mock_update_db, \
         patch.object(service, 'delete_document_from_database') as mock_delete_db:
        mock_get.return_value.json.return_value = {
            "value": [
                {
                    "@odata.type": "#microsoft.graph.driveItem",
                    "id": "folder-id",
                    "name": "MyFolder",
                    "folder": {},  # Indicates this is a folder
                    "webUrl": "http://example.com/folder",
                    "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                    "parentReference": {"driveId": "drive-id"}
                }
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None
        service.process_webhook_notification(notification)
        # Folder logic: should NOT call update_document_in_database or delete_document_from_database
        mock_update_db.assert_not_called()
        mock_delete_db.assert_not_called()
        captured = capsys.readouterr()
        assert "Folder created/updated: folder-id, Name: MyFolder" in captured.out

def test_process_webhook_notification_skips_document_with_no_content(service, capsys):
    notification = {
        "value": [
            {
                "resource": "drives/drive-id/items/item-id",
                "changeType": "updated"
            }
        ]
    }
    with patch.object(service, 'get_access_token', return_value="token"), \
         patch.object(service, 'get_delta_link', return_value=None), \
         patch("requests.get") as mock_get, \
         patch.object(service, 'save_delta_link'), \
         patch.object(service, 'get_document_content', return_value=None), \
         patch.object(service, 'update_document_in_database') as mock_update_db, \
         patch.object(service, 'delete_document_from_database'):
        mock_get.return_value.json.return_value = {
            "value": [
                {
                    "@odata.type": "#microsoft.graph.driveItem",
                    "id": "item-id",
                    "name": "TestDoc.txt",
                    "webUrl": "http://example.com",
                    "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                    "parentReference": {"driveId": "drive-id"}
                }
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None
        service.process_webhook_notification(notification)
        mock_update_db.assert_not_called()
        captured = capsys.readouterr()
        assert "Skipping document item-id as it could not be fetched." in captured.out

def test_process_webhook_notification_handles_deleted(service):
    notification = {
        "value": [
            {
                "resource": "drives/drive-id/items/item-id",
                "changeType": "updated"
            }
        ]
    }
    with patch.object(service, 'get_access_token', return_value="token"), \
         patch.object(service, 'get_delta_link', return_value=None), \
         patch("requests.get") as mock_get, \
         patch.object(service, 'save_delta_link'), \
         patch.object(service, 'delete_document_from_database') as mock_delete_db:
        mock_get.return_value.json.return_value = {
            "value": [
                {
                    "@odata.type": "#microsoft.graph.driveItem",
                    "id": "item-id",
                    "name": "TestDoc.txt",
                    "deleted": {},
                    "webUrl": "http://example.com",
                    "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                    "parentReference": {"driveId": "drive-id"}
                }
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None
        service.process_webhook_notification(notification)
        mock_delete_db.assert_called_once_with("item-id")

def test_process_webhook_notification_handles_no_changes(service, capsys):
    notification = {"value": [{"resource": "drives/drive-id/items/item-id", "changeType": "updated"}]}
    with patch.object(service, "get_access_token", return_value="token"), \
         patch.object(service, "get_delta_link", return_value=None), \
         patch("requests.get") as mock_get, \
         patch.object(service, "save_delta_link"), \
         patch.object(service, "get_document_content", return_value="test content"), \
         patch.object(service, "update_document_in_database"), \
         patch.object(service, "delete_document_from_database"):
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {"value": []}
        service.process_webhook_notification(notification)
        captured = capsys.readouterr()
        assert "No changes detected in the delta response." in captured.out
        
def test_process_webhook_notification_invalid_payload(service, capsys):
    notification = {}
    service.process_webhook_notification(notification)
    captured = capsys.readouterr()
    assert "Invalid notification payload: Missing 'value'" in captured.out

def test_process_webhook_notification_missing_resource(service, capsys):
    notification = {"value": [{"changeType": "updated"}]}
    service.process_webhook_notification(notification)
    captured = capsys.readouterr()
    assert "Invalid notification payload: Missing 'resource'" in captured.out

def test_process_webhook_notification_handles_exception(service, capsys):
    notification = {"value": [{"resource": "drives/drive-id/items/item-id", "changeType": "updated"}]}
    with patch.object(service, "get_access_token", side_effect=Exception("Token error")):
        service.process_webhook_notification(notification)
        captured = capsys.readouterr()
        assert "Error processing webhook notification: Token error" in captured.out
        
def test_get_drive_delta_success(service):
    with patch.object(service, 'get_access_token', return_value="token"), \
         patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"value": [{"id": "delta1"}]}
        mock_get.return_value.raise_for_status = lambda: None
        result = service.get_drive_delta("drive-id")
        assert result == [{"id": "delta1"}]
        mock_get.assert_called_once()

def test_get_drive_delta_failure(service):
    with patch.object(service, 'get_access_token', return_value="token"), \
         patch("requests.get", side_effect=Exception("fail")):
        result = service.get_drive_delta("drive-id")
        assert result == []

def test_save_delta_link(service):
    mock_collection = MagicMock()
    service.collection = mock_collection
    service.save_delta_link("resource", "delta-link")
    mock_collection.update_one.assert_called_once_with(
        {"resource": "resource"},
        {"$set": {"delta_link": "delta-link"}},
        upsert=True
    )
    
def test_save_delta_link_exception(capsys):
    service = MagicMock()
    service.collection.update_one.side_effect = Exception("DB error")
    from app.services.sharepoint_service import SharePointService
    SharePointService.save_delta_link(service, "resource", "delta-link")
    captured = capsys.readouterr()
    assert "Error saving delta link for resource resource: DB error" in captured.out

def test_get_delta_link_found(service):
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"delta_link": "link123"}
    service.collection = mock_collection
    result = service.get_delta_link("resource")
    assert result == "link123"

def test_get_delta_link_not_found(service):
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = None
    service.collection = mock_collection
    result = service.get_delta_link("resource")
    assert result is None
    
def test_get_delta_link_exception(capsys):
    service = MagicMock()
    service.collection.find_one.side_effect = Exception("DB error")
    from app.services.sharepoint_service import SharePointService
    result = SharePointService.get_delta_link(service, "resource")
    assert result is None
    captured = capsys.readouterr()
    assert "Error retrieving delta link for resource resource: DB error" in captured.out

def test_update_document_in_database_success(service):
    # Patch dependencies and simulate chunking and embedding
    with patch("app.services.sharepoint_service.RecursiveCharacterTextSplitter") as mock_splitter, \
         patch("app.services.sharepoint_service.get_document_permissions", return_value={"users": [], "groups": [], "access_level": "private"}), \
         patch("app.services.sharepoint_service.get_embedding_model"), \
         patch("app.services.sharepoint_service.MongoDBAtlasVectorSearch.from_documents") as mock_from_docs:
        mock_splitter.return_value.split_text.return_value = ["chunk1", "chunk2"]
        mock_collection = MagicMock()
        service.collection = mock_collection
        service.update_document_in_database(
            document_id="doc1",
            document_name="DocName",
            content="Some content",
            drive_id="drive1",
            web_url="http://url",
            last_modified="2024-01-01T00:00:00Z"
        )
        mock_collection.delete_many.assert_called_once_with({"documentId": "doc1"})
        assert mock_from_docs.called
        
def test_update_document_in_database_handles_empty_content(service, capsys):
    with patch("app.services.sharepoint_service.RecursiveCharacterTextSplitter") as mock_splitter, \
         patch("app.services.sharepoint_service.get_document_permissions", return_value={"users": [], "groups": [], "access_level": "private"}), \
         patch("app.services.sharepoint_service.get_embedding_model"), \
         patch.object(service, "collection"):
        mock_splitter.return_value.split_text.return_value = []
        service.update_document_in_database("docid", "docname", "content", "driveid", "url", "2024-01-01T00:00:00Z")
        captured = capsys.readouterr()
        assert "No content to update for document docname" in captured.out

def test_delete_document_from_database_found(service):
    mock_collection = MagicMock()
    mock_collection.delete_many.return_value.deleted_count = 1
    service.collection = mock_collection
    service.delete_document_from_database("doc1")
    mock_collection.delete_many.assert_called_once_with({"documentId": "doc1"})

def test_delete_document_from_database_not_found(service):
    mock_collection = MagicMock()
    mock_collection.delete_many.return_value.deleted_count = 0
    service.collection = mock_collection
    service.delete_document_from_database("doc1")
    mock_collection.delete_many.assert_called_once_with({"documentId": "doc1"})

def test_delete_document_from_database_handles_exception(service, capsys):
    mock_collection = MagicMock()
    mock_collection.delete_many.side_effect = Exception("DB error")
    service.collection = mock_collection
    service.delete_document_from_database("docid")
    captured = capsys.readouterr()
    assert "Error deleting document docid from the database: DB error" in captured.out