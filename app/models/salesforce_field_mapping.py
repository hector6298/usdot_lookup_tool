from sqlmodel import Field, SQLModel
from typing import List, TYPE_CHECKING, ClassVar, Dict, Any

if TYPE_CHECKING:
    from app.models.user_org_membership import AppOrg

class SalesforceFieldMapping(SQLModel, table=True):
    """Represents field mappings between carrier data and Salesforce fields for an organization."""
    id: int = Field(primary_key=True)
    org_id: str = Field(foreign_key="apporg.org_id")
    carrier_field: str  # Field name in CarrierData model (e.g., 'legal_name', 'phone')
    salesforce_field: str  # Salesforce field API name (e.g., 'Name', 'Phone', 'Custom_Field__c')
    is_active: bool = Field(default=True)
    field_type: str = Field(default="text")  # text, number, date, boolean
    
    # Standard Salesforce fields that are commonly used
    STANDARD_SALESFORCE_FIELDS: ClassVar[Dict[str, str]] = {
        "Name": "Account Name",
        "Phone": "Phone Number", 
        "Website": "Website",
        "BillingStreet": "Billing Street",
        "BillingCity": "Billing City",
        "BillingState": "Billing State/Province",
        "BillingPostalCode": "Billing Zip/Postal Code",
        "BillingCountry": "Billing Country",
        "ShippingStreet": "Shipping Street",
        "ShippingCity": "Shipping City", 
        "ShippingState": "Shipping State/Province",
        "ShippingPostalCode": "Shipping Zip/Postal Code",
        "ShippingCountry": "Shipping Country",
        "AccountNumber": "Account Number",
        "Type": "Account Type",
        "Industry": "Industry",
        "Description": "Description",
        "NumberOfEmployees": "Employees",
        "AnnualRevenue": "Annual Revenue"
    }
    
    # Available carrier fields with their display names
    AVAILABLE_CARRIER_FIELDS: ClassVar[Dict[str, Dict[str, str]]] = {
        "usdot": {"label": "USDOT Number", "type": "text"},
        "entity_type": {"label": "Entity Type", "type": "text"},
        "usdot_status": {"label": "USDOT Status", "type": "text"},
        "legal_name": {"label": "Legal Name", "type": "text"},
        "dba_name": {"label": "DBA Name", "type": "text"},
        "physical_address": {"label": "Physical Address", "type": "text"},
        "mailing_address": {"label": "Mailing Address", "type": "text"},
        "phone": {"label": "Phone Number", "type": "text"},
        "state_carrier_id": {"label": "State Carrier ID", "type": "text"},
        "mc_mx_ff_numbers": {"label": "MC/MX/FF Numbers", "type": "text"},
        "duns_number": {"label": "DUNS Number", "type": "text"},
        "power_units": {"label": "Power Units", "type": "number"},
        "drivers": {"label": "Number of Drivers", "type": "number"},
        "mcs_150_form_date": {"label": "MCS-150 Form Date", "type": "date"},
        "mcs_150_mileage_year_mileage": {"label": "MCS-150 Mileage", "type": "number"},
        "mcs_150_mileage_year_year": {"label": "MCS-150 Mileage Year", "type": "number"},
        "out_of_service_date": {"label": "Out of Service Date", "type": "date"},
        "operating_authority_status": {"label": "Operating Authority Status", "type": "text"},
        "operation_classification": {"label": "Operation Classification", "type": "text"},
        "carrier_operation": {"label": "Carrier Operation", "type": "text"},
        "hm_shipper_operation": {"label": "HM Shipper Operation", "type": "text"},
        "cargo_carried": {"label": "Cargo Carried", "type": "text"},
        "usa_vehicle_inspections": {"label": "USA Vehicle Inspections", "type": "number"},
        "usa_vehicle_out_of_service": {"label": "USA Vehicle Out of Service", "type": "number"},
        "usa_vehicle_out_of_service_percent": {"label": "USA Vehicle Out of Service %", "type": "text"},
        "usa_vehicle_national_average": {"label": "USA Vehicle National Average", "type": "text"},
        "usa_driver_inspections": {"label": "USA Driver Inspections", "type": "number"},
        "usa_driver_out_of_service": {"label": "USA Driver Out of Service", "type": "number"},
        "usa_driver_out_of_service_percent": {"label": "USA Driver Out of Service %", "type": "text"},
        "usa_driver_national_average": {"label": "USA Driver National Average", "type": "text"},
        "usa_hazmat_inspections": {"label": "USA Hazmat Inspections", "type": "number"},
        "usa_hazmat_out_of_service": {"label": "USA Hazmat Out of Service", "type": "number"},
        "usa_hazmat_out_of_service_percent": {"label": "USA Hazmat Out of Service %", "type": "text"},
        "usa_hazmat_national_average": {"label": "USA Hazmat National Average", "type": "text"},
        "usa_iep_inspections": {"label": "USA IEP Inspections", "type": "number"},
        "usa_iep_out_of_service": {"label": "USA IEP Out of Service", "type": "number"},
        "usa_iep_out_of_service_percent": {"label": "USA IEP Out of Service %", "type": "text"},
        "usa_iep_national_average": {"label": "USA IEP National Average", "type": "text"},
        "usa_crashes_tow": {"label": "USA Crashes (Tow)", "type": "number"},
        "usa_crashes_fatal": {"label": "USA Crashes (Fatal)", "type": "number"},
        "usa_crashes_injury": {"label": "USA Crashes (Injury)", "type": "number"},
        "usa_crashes_total": {"label": "USA Crashes (Total)", "type": "number"},
        "canada_driver_out_of_service": {"label": "Canada Driver Out of Service", "type": "number"},
        "canada_driver_out_of_service_percent": {"label": "Canada Driver Out of Service %", "type": "text"},
        "canada_driver_inspections": {"label": "Canada Driver Inspections", "type": "number"},
        "canada_vehicle_out_of_service": {"label": "Canada Vehicle Out of Service", "type": "number"},
        "canada_vehicle_out_of_service_percent": {"label": "Canada Vehicle Out of Service %", "type": "text"},
        "canada_vehicle_inspections": {"label": "Canada Vehicle Inspections", "type": "number"},
        "canada_crashes_tow": {"label": "Canada Crashes (Tow)", "type": "number"},
        "canada_crashes_fatal": {"label": "Canada Crashes (Fatal)", "type": "number"},
        "canada_crashes_injury": {"label": "Canada Crashes (Injury)", "type": "number"},
        "canada_crashes_total": {"label": "Canada Crashes (Total)", "type": "number"},
        "safety_rating_date": {"label": "Safety Rating Date", "type": "date"},
        "safety_review_date": {"label": "Safety Review Date", "type": "date"},
        "safety_rating": {"label": "Safety Rating", "type": "text"},
        "safety_type": {"label": "Safety Type", "type": "text"},
        "latest_update": {"label": "Latest Update", "type": "date"},
        "url": {"label": "URL", "type": "text"}
    }
