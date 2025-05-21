import os
import sys
# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.sharepoint_service import SharePointService
from app.core.config import settings

def main():
    """
    Script to ensure a SharePoint webhook subscription is active.
    If a subscription exists, it will be renewed. Otherwise, a new subscription will be created.
    """
    notification_url = settings.WEBHOOK_CALLBACK_URL

    try:
        sharepoint_service = SharePointService()

         # Get the list of drives and extract the first drive ID
        drives = sharepoint_service.list_drives()
        #for drive in drives:
        #    print(f"Drive ID: {drive['id']}, Name: {drive['name']}") 
        if not drives:
            print("No drives found in the SharePoint site.")
            return

        drive_id = drives[0]["id"]  # Use the first drive for the subscription
        resource = f"drives/{drive_id}/root"
        
        #print(f"Targeting resource: {resource}")
        # Get all active subscriptions
        subscriptions = sharepoint_service.get_webhook_subscriptions()

        # Check if a subscription for the given resource already exists
        for subscription in subscriptions:
            if subscription["resource"] == resource:
                subscription_id = subscription["id"]
                print(f"Found existing subscription: {subscription_id}. Renewing it...")

                try:
                    # Attempt to renew the subscription
                    sharepoint_service.renew_webhook_subscription(subscription_id)
                    print("Subscription renewed successfully.")
                    return
                except Exception as e:
                    print(f"Failed to renew subscription {subscription_id}: {e}")
                    print("Deleting the failed subscription...")
                    try:
                        sharepoint_service.delete_webhook_subscription(subscription_id)
                        print(f"Subscription {subscription_id} deleted successfully.")
                    except Exception as delete_error:
                        print(f"Failed to delete subscription {subscription_id}: {delete_error}")
                    print("Creating a new subscription instead...")
                    break  # Exit the loop to create a new subscription

        # If no valid subscription exists, create a new one
        print("No valid subscription found. Creating a new one...")
        sharepoint_service.create_webhook_subscription(resource, notification_url)
        print("Webhook registered")

    except Exception as e:
        print(f"Error ensuring webhook subscription: {e}")


if __name__ == "__main__":
    main()