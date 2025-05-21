"""
Optimized document permission service
"""

import requests
from typing import Dict, Any, List, Set
from app.core.config import settings

def get_org_domains() -> List[str]:
    """Get organization domains from environment"""
    domains = getattr(settings, 'ORG_DOMAINS', 'microweb.global,microwebglobal.onmicrosoft.com')
    return [d.strip().lower() for d in domains.split(',') if d.strip()]

def check_user_group_membership(user_email: str, groups: List[str], sharepoint_service) -> bool:
    """
    Optimized group membership check
    """
    try:
        user_domain = user_email.split("@")[1].lower() if "@" in user_email else ""
        org_domains = get_org_domains()
        
        if user_domain in org_domains:
            sharepoint_site_groups = ["demo Owners", "demo Members", "demo Visitors"]
            has_sharepoint_groups = any(group in sharepoint_site_groups for group in groups)
            if has_sharepoint_groups:
                return True
        
        azure_ad_groups = [g for g in groups if "@" in g or (len(g) > 30 and not g.startswith("demo "))]
        if not azure_ad_groups:
            return False
        
        token = sharepoint_service.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        user_groups_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/memberOf"
        response = requests.get(user_groups_endpoint, headers=headers)
        
        if response.status_code != 200:
            return False
        
        user_groups = response.json().get("value", [])
        user_group_names = {g.get("displayName", "").lower() for g in user_groups}
        user_group_emails = {g.get("mail", "").lower() for g in user_groups if g.get("mail")}
        
        for group in azure_ad_groups:
            if group.lower() in user_group_names or group.lower() in user_group_emails:
                return True
        
        return False
        
    except Exception as e:
        return False

def is_user_in_organization(user_email: str, sharepoint_service=None) -> bool:
    """
    Check if user belongs to organization using domain validation
    """
    user_domain = user_email.split("@")[1].lower() if "@" in user_email else ""
    org_domains = get_org_domains()
    return user_domain in org_domains

def get_document_permissions(sharepoint_service, doc_id: str, drive_id: str) -> Dict[str, Any]:
    """
    Get comprehensive permission details for a document
    """
    token = sharepoint_service.get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    permissions_endpoint = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{doc_id}/permissions"
    try:
        response = requests.get(permissions_endpoint, headers=headers)
        response.raise_for_status()
        permissions_data = response.json()
        permissions = permissions_data.get("value", [])
        
        result = {
            "users": set(),
            "groups": set(),
            "access_level": "private",
            "inheritance": False,
            "sharing_links": [],
            "raw_permissions": permissions
        }
        
        for permission in permissions:
            process_permission_entry(permission, result, sharepoint_service, token)
        
        result["users"] = list(result["users"])
        result["groups"] = list(result["groups"])
        
        if result["sharing_links"]:
            for link in result["sharing_links"]:
                if link["scope"] == "anonymous":
                    result["access_level"] = "public"
                    break
                elif link["scope"] == "organization" and result["access_level"] != "public":
                    result["access_level"] = "organization"
        
        if result["users"] or result["groups"]:
            if result["access_level"] == "private":
                result["access_level"] = "restricted"
        
        return result
        
    except Exception as e:
        return {"users": [], "groups": [], "access_level": "private", "error": str(e)}

def process_permission_entry(permission: Dict, result: Dict, sharepoint_service, token: str):
    """
    Process a single permission entry
    """
    link = permission.get("link", {})
    if link:
        scope = link.get("scope", "")
        link_type = link.get("type", "")
        
        sharing_link = {
            "type": link_type,
            "scope": scope,
            "webUrl": link.get("webUrl", ""),
            "application": link.get("application", {}).get("id", "") if link.get("application") else ""
        }
        result["sharing_links"].append(sharing_link)
        
        if scope == "anonymous":
            result["access_level"] = "public"
        elif scope == "organization":
            result["access_level"] = "organization"
    
    granted_to_v2 = permission.get("grantedToV2", {})
    if granted_to_v2:
        process_granted_entity(granted_to_v2, result, sharepoint_service, token)
    
    granted_to = permission.get("grantedTo", {})
    if granted_to:
        process_granted_entity(granted_to, result, sharepoint_service, token)
    
    granted_to_identities = permission.get("grantedToIdentities", [])
    for identity in granted_to_identities:
        process_granted_entity(identity, result, sharepoint_service, token)
    
    if permission.get("inheritedFrom"):
        result["inheritance"] = True

def process_granted_entity(entity: Dict, result: Dict, sharepoint_service, token: str):
    """
    Process a granted entity (user, group, or application)
    """
    user = entity.get("user", {})
    if user:
        email = user.get("email", "").lower().strip()
        if email and email not in result["users"]:
            result["users"].add(email)
    
    site_group = entity.get("siteGroup", {})
    if site_group:
        group_display_name = site_group.get("displayName", "")
        group_id = site_group.get("id", "")
        group_login_name = site_group.get("loginName", "")
        
        if group_display_name:
            result["groups"].add(group_display_name)
        elif group_login_name:
            result["groups"].add(group_login_name)
        elif group_id:
            result["groups"].add(group_id)
    
    group = entity.get("group", {})
    if group:
        group_id = group.get("id", "")
        group_email = group.get("email", "")
        group_display_name = group.get("displayName", "")
        
        if group_id and not group_email:
            group_details = get_group_details(group_id, token)
            if group_details:
                group_email = group_details.get("mail", "") or group_details.get("userPrincipalName", "")
        
        if group_email:
            result["groups"].add(group_email.lower().strip())
        elif group_display_name:
            result["groups"].add(group_display_name)
        elif group_id:
            result["groups"].add(group_id)
    
    application = entity.get("application", {})
    if application:
        app_id = application.get("id", "")
        app_display_name = application.get("displayName", "")

def get_group_details(group_id: str, token: str) -> Dict:
    """
    Get additional details about a group from Microsoft Graph
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        group_endpoint = f"https://graph.microsoft.com/v1.0/groups/{group_id}"
        
        response = requests.get(group_endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {}