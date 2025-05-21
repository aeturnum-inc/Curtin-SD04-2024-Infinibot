from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from app.services.sharepoint_service import SharePointService

router = APIRouter()

@router.post("/webhook")
async def webhook_listener(request: Request):
    """
    Endpoint to receive SharePoint webhook notifications.
    """
    try:
        # Handle validation request
        validation_token = request.query_params.get("validationToken")
        if validation_token:
            print(f"Validation token received: {validation_token}")
            return Response(content=validation_token, media_type="text/plain") # Respond with the validation token
        
    
        #handle notifications
        notification = await request.json()
        #print(f"Notification received: {notification}")
        sharepoint_service = SharePointService()
        sharepoint_service.process_webhook_notification(notification)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing webhook: {str(e)}")