# Import all models here to ensure they are registered with SQLModel
from .carrier_data import CarrierData, CarrierDataCreate
from .engagement import CarrierEngagementStatus, CarrierChangeItem, CarrierChangeRequest, CarrierWithEngagementResponse
from .oauth import OAuthToken
from .ocr_results import OCRResult, OCRResultCreate, OCRResultResponse
from .user_org_membership import UserOrgMembership, AppUser, AppOrg
from .sobject_sync_history import CRMObjectSyncHistory, SObjectSyncHistory
from .sobject_sync_status import CRMSyncStatus, SObjectSyncStatus

__all__ = [
    "CarrierData",
    "CarrierDataCreate", 
    "CarrierEngagementStatus",
    "CarrierChangeItem",
    "CarrierChangeRequest",
    "CarrierWithEngagementResponse",
    "OAuthToken",
    "OCRResult",
    "OCRResultCreate",
    "OCRResultResponse",
    "UserOrgMembership",
    "AppUser",
    "AppOrg",
    "CRMObjectSyncHistory",
    "SObjectSyncHistory",  # Keep for backward compatibility
    "CRMSyncStatus", 
    "SObjectSyncStatus",  # Keep for backward compatibility
]