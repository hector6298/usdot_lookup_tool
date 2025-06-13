from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import List, Optional
from pydantic import computed_field, ConfigDict
from sqlmodel import Relationship

class OCRResultCreate(SQLModel):
    """Schema for creating a new OCR result."""
    extracted_text: str | None = Field(default=None, max_length=250)
    filename: str = Field(nullable=False, max_length=250)
    user_id: str = Field(nullable=False)
    org_id: str = Field(nullable=False)
    
class OCRResult(SQLModel, table=True):
    """Represents an OCR result in the database."""    
    model_config = ConfigDict(
        orm_mode = True 
    )
    id: int = Field(default=None, primary_key=True)
    extracted_text: str | None = Field(default=None, max_length=250)
    dot_reading: str | None = Field(default=None, max_length=32, foreign_key="carrierdata.usdot")
    filename: str = Field(nullable=False, max_length=250)
    timestamp: datetime = Field(nullable=False)
    user_id: str = Field(nullable=False)
    org_id: str = Field(nullable=False)
    
    carrier_data: Optional["CarrierData"] = Relationship(back_populates="ocr_results")

class OCRResultResponse(SQLModel):
    """Schema for returning OCR result data."""
    dot_reading: str | None
    legal_name: str | None
    phone: str | None
    mailing_address: str | None
    timestamp: str
    filename: str
    user_id: str
    org_id: str
    
class CarrierChangeItem(SQLModel):
    """Schema for carrier checkbox input."""
    usdot: str
    field: str
    value: bool | datetime | str

class CarrierChangeRequest(SQLModel):
    """Schema for carrier checkbox input."""
    changes: List[CarrierChangeItem] = Field(default_factory=list)

    
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
    mcs_150_mileage_year_mileage: Optional[int] = None
    mcs_150_mileage_year_year: Optional[int] = None
    out_of_service_date: Optional[str] = None  # Consider changing to datetime
    operating_authority_status: Optional[str] = None
    operation_classification: Optional[str] = None
    carrier_operation: Optional[str] = None
    hm_shipper_operation: Optional[str] = None
    cargo_carried: Optional[str] = None
    
    usa_vehicle_inspections: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_vehicle_inspections"}
    )
    usa_vehicle_out_of_service: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_vehicle_out_of_service"}
    )
    usa_vehicle_out_of_service_percent: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_vehicle_out_of_service_percent"}
    )
    usa_vehicle_national_average: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_vehicle_national_average"}
    )
    usa_driver_inspections: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_driver_inspections"}
    )
    usa_driver_out_of_service: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_driver_out_of_service"}
    )
    usa_driver_out_of_service_percent: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_driver_out_of_service_percent"}
    )
    usa_driver_national_average: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_driver_national_average"}
    )
    usa_hazmat_inspections: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_hazmat_inspections"}
    )
    usa_hazmat_out_of_service: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_hazmat_out_of_service"}
    )
    usa_hazmat_out_of_service_percent: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_hazmat_out_of_service_percent"}
    )
    usa_hazmat_national_average: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_hazmat_national_average"}
    )
    usa_iep_inspections: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_iep_inspections"}
    )
    usa_iep_out_of_service: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_inspections_iep_out_of_service"}
    )
    usa_iep_out_of_service_percent: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_iep_out_of_service_percent"}
    )
    usa_iep_national_average: Optional[str] = Field(
        schema_extra={"validation_alias":"united_states_inspections_iep_national_average"}
    )
    
    usa_crashes_tow: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_crashes_tow"}
    )
    usa_crashes_fatal: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_crashes_fatal"}
    )
    usa_crashes_injury: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_crashes_injury"}
    )
    usa_crashes_total: Optional[int] = Field(
        schema_extra={"validation_alias":"united_states_crashes_total"}
    )
    
    canada_driver_out_of_service: Optional[int] = Field(
        schema_extra={"validation_alias":"canada_inspections_driver_out_of_service"}
    )
    canada_driver_out_of_service_percent: Optional[str] = Field(
        schema_extra={"validation_alias":"canada_inspections_driver_out_of_service_percent"}
    )
    canada_driver_inspections: Optional[int] = Field(
        schema_extra={"validation_alias":"canada_inspections_driver_inspections"}
    )
    canada_vehicle_out_of_service: Optional[int] = Field(
        schema_extra={"validation_alias":"canada_inspections_vehicle_out_of_service"}
    )
    canada_vehicle_out_of_service_percent: Optional[str] = Field(
        schema_extra={"validation_alias":"canada_inspections_vehicle_out_of_service_percent"}
    )
    canada_vehicle_inspections: Optional[int] = Field(
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

    # Relationship attributes
    ocr_results: List[OCRResult] = Relationship(back_populates="carrier_data")
    carrier_engagement_status: Optional["CarrierEngagementStatus"] = Relationship(back_populates="carrier_data")


class CarrierEngagementStatus(SQLModel, table=True):
    usdot: str = Field(foreign_key="carrierdata.usdot", primary_key=True)
    org_id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    carrier_interested: bool = Field(default=False, nullable=False)
    carrier_interested_timestamp: datetime = Field(default=None, nullable=True)
    carrier_interested_by_user_id: str = Field(default=None, nullable=True)

    carrier_contacted: bool = Field(default=False, nullable=False)
    carrier_contacted_timestamp: datetime = Field(default=None, nullable=True)
    carrier_contacted_by_user_id: str = Field(default=None, nullable=True)

    carrier_followed_up: bool = Field(default=False, nullable=False)
    carrier_followed_up_timestamp: datetime = Field(default=None, nullable=True)
    carrier_followed_up_by_user_id: str = Field(default=None, nullable=True)
    carrier_follow_up_by_date: datetime = Field(default=None, nullable=True)

    carrier_emailed: bool = Field(default=False, nullable=False)
    carrier_emailed_timestamp: datetime = Field(default=None, nullable=True)
    carrier_emailed_by_user_id: str = Field(default=None, nullable=True)
    rental_notes: str | None = Field(default=None, max_length=360)

    # Relationship attributes
    carrier_data: Optional["CarrierData"] = Relationship(back_populates="carrier_engagement_status")

class CarrierWithEngagementResponse(SQLModel):
    usdot: str
    legal_name: str
    phone: Optional[str]
    mailing_address: str
    created_at: str
    carrier_interested: bool
    carrier_contacted: bool
    carrier_followed_up: bool
    carrier_follow_up_by_date: Optional[str]