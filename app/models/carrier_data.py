from sqlmodel import Field, SQLModel
from typing import List, Optional, TYPE_CHECKING
from pydantic import ConfigDict
from sqlmodel import Relationship
from sqlalchemy import Column, BigInteger

if TYPE_CHECKING:
    from app.models.ocr_results import OCRResult
    from app.models.engagement import CarrierEngagementStatus
    from app.models.sobject_sync_status import SObjectSyncStatus

class CarrierDataCreate(SQLModel):
    model_config = ConfigDict(
        populate_by_name=True,
        orm_mode = True 
    )
    usdot: str
    entity_type: Optional[str] = None
    usdot_status: Optional[str] = None
    legal_name: Optional[str] = None
    dba_name: Optional[str] = None
    physical_address: Optional[str] = None
    mailing_address: Optional[str] = None
    phone: Optional[str] = None
    state_carrier_id: Optional[str] = None
    mc_mx_ff_numbers: Optional[str] = None
    duns_number: Optional[str] = None
    power_units: Optional[int] = None
    drivers: Optional[int] = None
    mcs_150_form_date: Optional[str] = None  # Consider changing to datetime
    mcs_150_mileage_year_mileage: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger)
    )
    mcs_150_mileage_year_year: Optional[int] = None
    out_of_service_date: Optional[str] = None  # Consider changing to datetime
    operating_authority_status: Optional[str] = None
    operation_classification: Optional[str] = None
    carrier_operation: Optional[str] = None
    hm_shipper_operation: Optional[str] = None
    cargo_carried: Optional[str] = None
    
    usa_vehicle_inspections: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_vehicle_inspections"}
    )
    usa_vehicle_out_of_service: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_vehicle_out_of_service"}
    )
    usa_vehicle_out_of_service_percent: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_vehicle_out_of_service_percent"}
    )
    usa_vehicle_national_average: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_vehicle_national_average"}
    )
    usa_driver_inspections: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_driver_inspections"}
    )
    usa_driver_out_of_service: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_driver_out_of_service"}
    )
    usa_driver_out_of_service_percent: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_driver_out_of_service_percent"}
    )
    usa_driver_national_average: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_driver_national_average"}
    )
    usa_hazmat_inspections: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_hazmat_inspections"}
    )
    usa_hazmat_out_of_service: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_hazmat_out_of_service"}
    )
    usa_hazmat_out_of_service_percent: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_hazmat_out_of_service_percent"}
    )
    usa_hazmat_national_average: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_hazmat_national_average"}
    )
    usa_iep_inspections: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_iep_inspections"}
    )
    usa_iep_out_of_service: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_iep_out_of_service"}
    )
    usa_iep_out_of_service_percent: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_iep_out_of_service_percent"}
    )
    usa_iep_national_average: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_inspections_iep_national_average"}
    )
    
    usa_crashes_tow: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_crashes_tow"}
    )
    usa_crashes_fatal: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_crashes_fatal"}
    )
    usa_crashes_injury: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_crashes_injury"}
    )
    usa_crashes_total: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"united_states_crashes_total"}
    )
    
    canada_driver_out_of_service: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"canada_inspections_driver_out_of_service"}
    )
    canada_driver_out_of_service_percent: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"canada_inspections_driver_out_of_service_percent"}
    )
    canada_driver_inspections: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"canada_inspections_driver_inspections"}
    )
    canada_vehicle_out_of_service: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"canada_inspections_vehicle_out_of_service"}
    )
    canada_vehicle_out_of_service_percent: Optional[str] = Field(
        default=None,
        schema_extra={"validation_alias":"canada_inspections_vehicle_out_of_service_percent"}
    )
    canada_vehicle_inspections: Optional[int] = Field(
        default=None,
        schema_extra={"validation_alias":"canada_inspections_vehicle_inspections"}
    )
    
    canada_crashes_tow: Optional[int] = None
    canada_crashes_fatal: Optional[int] = None
    canada_crashes_injury: Optional[int] = None
    canada_crashes_total: Optional[int] = None
    
    safety_rating_date: Optional[str] = None  # Consider changing to datetime
    safety_review_date: Optional[str] = None  # Consider changing to datetime
    safety_rating: Optional[str] = None
    safety_type: Optional[str] = None
    
    latest_update: Optional[str] = None  # Consider changing to datetime
    url: Optional[str] = None

    lookup_success_flag: bool


class CarrierData(SQLModel, table=True):
    model_config = ConfigDict(
        populate_by_name=True,
        orm_mode = True 
    )
    usdot: str = Field(primary_key=True)
    entity_type: Optional[str] = None
    usdot_status: Optional[str] = None
    legal_name: Optional[str] = None
    dba_name: Optional[str] = None
    physical_address: Optional[str] = None
    mailing_address: Optional[str] = None
    phone: Optional[str] = None
    state_carrier_id: Optional[str] = None
    mc_mx_ff_numbers: Optional[str] = None
    duns_number: Optional[str] = None
    power_units: Optional[int] = None
    drivers: Optional[int] = None
    mcs_150_form_date: Optional[str] = None  # Consider changing to datetime
    mcs_150_mileage_year_mileage: Optional[int] = Field(
        sa_column=Column(BigInteger)
    )
    mcs_150_mileage_year_year: Optional[int] = None
    out_of_service_date: Optional[str] = None  # Consider changing to datetime
    operating_authority_status: Optional[str] = None
    operation_classification: Optional[str] = None
    carrier_operation: Optional[str] = None
    hm_shipper_operation: Optional[str] = None
    cargo_carried: Optional[str] = None
    
    usa_vehicle_inspections: Optional[int] = None
    usa_vehicle_out_of_service: Optional[int] = None
    usa_vehicle_out_of_service_percent: Optional[str] = None
    usa_vehicle_national_average: Optional[str] = None
    usa_driver_inspections: Optional[int] = None 
    usa_driver_out_of_service: Optional[int] = None 
    usa_driver_out_of_service_percent: Optional[str] = None
    usa_driver_national_average: Optional[str] = None 
    usa_hazmat_inspections: Optional[int] = None 
    usa_hazmat_out_of_service: Optional[int] = None 
    usa_hazmat_out_of_service_percent: Optional[str] = None
    usa_hazmat_national_average: Optional[str] = None 
    usa_iep_inspections: Optional[int] = None 
    usa_iep_out_of_service: Optional[int] = None 
    usa_iep_out_of_service_percent: Optional[str]  = None
    usa_iep_national_average: Optional[str] = None 
    
    usa_crashes_tow: Optional[int]  = None
    usa_crashes_fatal: Optional[int]  = None
    usa_crashes_injury: Optional[int]  = None
    usa_crashes_total: Optional[int] = None
    
    canada_driver_out_of_service: Optional[int]  = None
    canada_driver_out_of_service_percent: Optional[str] = None
    canada_driver_inspections: Optional[int]  = None
    canada_vehicle_out_of_service: Optional[int]  = None
    canada_vehicle_out_of_service_percent: Optional[str] = None
    canada_vehicle_inspections: Optional[int]  = None
    
    canada_crashes_tow: Optional[int] = None
    canada_crashes_fatal: Optional[int] = None
    canada_crashes_injury: Optional[int] = None
    canada_crashes_total: Optional[int] = None
    
    safety_rating_date: Optional[str] = None  # Consider changing to datetime
    safety_review_date: Optional[str] = None  # Consider changing to datetime
    safety_rating: Optional[str] = None
    safety_type: Optional[str] = None
    
    latest_update: Optional[str] = None  # Consider changing to datetime
    url: Optional[str] = None

    # Relationship attributes
    ocr_results: List["OCRResult"] = Relationship(back_populates="carrier_data")
    carrier_engagement_status: Optional["CarrierEngagementStatus"] = Relationship(back_populates="carrier_data")
    sync_status: List["SObjectSyncStatus"] = Relationship(back_populates="carrier_data", cascade_delete=True)
