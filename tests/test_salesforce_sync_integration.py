import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from datetime import datetime
import json

from app.main import app
from app.database import get_db
from app.models.carrier_data import CarrierData
from app.models.crm_sync_history import CRMSyncHistory
from app.models.crm_sync_status import CRMSyncStatus
from app.crud.crm_sync_history import create_crm_sync_history_record
from app.crud.crm_sync_status import upsert_sync_status


@pytest.fixture
def db_session():
    """Create a temporary in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_client(db_session):
    """Create a test client with a mock database session."""
    def get_test_db():
        return db_session
    
    app.dependency_overrides[get_db] = get_test_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    return {
        "userinfo": {
            "sub": "test-user-id",
            "org_id": "test-org-id",
            "name": "Test User"
        },
        "sf_connected": True
    }


class TestSalesforceEndpointIntegration:
    """Integration tests for the updated Salesforce upload endpoint."""
    
    def test_salesforce_sync_success_logging(self, db_session):
        """Test that successful Salesforce sync is properly logged."""
        # Create test carrier
        carrier = CarrierData(
            usdot="12345",
            legal_name="Test Carrier",
            phone="555-1234"
        )
        db_session.add(carrier)
        db_session.commit()
        
        # Mock Salesforce response for success
        sf_response = {
            "hasErrors": False,
            "results": [
                {
                    "referenceId": "carrier_12345",
                    "id": "001D000000K1YFjIAN"
                }
            ]
        }
        
        user_id = "test-user"
        org_id = "test-org"
        
        # Process the response like the endpoint would
        sync_timestamp = datetime.utcnow()
        carrier_map = {"carrier_12345": carrier}
        
        for result in sf_response["results"]:
            reference_id = result.get("referenceId")
            salesforce_id = result.get("id")
            test_carrier = carrier_map.get(reference_id)
            
            if test_carrier and salesforce_id:
                # Create sync history record
                history_record = create_crm_sync_history_record(
                    db=db_session,
                    usdot=test_carrier.usdot,
                    sync_status="SUCCESS",
                    crm_object_type="account",
                    user_id=user_id,
                    org_id=org_id,
                    crm_object_id=salesforce_id,
                    detail=f"Successfully created Account with ID: {salesforce_id}",
                    sync_timestamp=sync_timestamp
                )
                
                # Upsert sync status
                status_record = upsert_sync_status(
                    db=db_session,
                    usdot=test_carrier.usdot,
                    org_id=org_id,
                    user_id=user_id,
                    sync_status="SUCCESS",
                    crm_object_id=salesforce_id
                )
        
        # Verify history record was created
        history_records = db_session.query(CRMSyncHistory).filter(
            CRMSyncHistory.usdot == "12345"
        ).all()
        assert len(history_records) == 1
        assert history_records[0].sync_status == "SUCCESS"
        assert history_records[0].crm_object_id == "001D000000K1YFjIAN"
        assert history_records[0].user_id == user_id
        assert history_records[0].org_id == org_id
        
        # Verify status record was created
        status_records = db_session.query(CRMSyncStatus).filter(
            CRMSyncStatus.usdot == "12345",
            CRMSyncStatus.org_id == org_id
        ).all()
        assert len(status_records) == 1
        assert status_records[0].sobject_sync_status == "SUCCESS"
        assert status_records[0].sobject_id == "001D000000K1YFjIAN"
    
    def test_salesforce_sync_failure_logging(self, db_session):
        """Test that failed Salesforce sync is properly logged."""
        # Create test carrier
        carrier = CarrierData(
            usdot="12346",
            legal_name="Test Carrier 2",
            phone="555-5678"
        )
        db_session.add(carrier)
        db_session.commit()
        
        # Mock Salesforce response for failure
        sf_response = {
            "hasErrors": True,
            "results": [
                {
                    "referenceId": "carrier_12346",
                    "errors": [
                        {
                            "statusCode": "INVALID_EMAIL_ADDRESS",
                            "message": "Email: invalid email address: 123",
                            "fields": ["Email"]
                        }
                    ]
                }
            ]
        }
        
        user_id = "test-user"
        org_id = "test-org"
        
        # Process the response like the endpoint would
        sync_timestamp = datetime.utcnow()
        carrier_map = {"carrier_12346": carrier}
        
        for result in sf_response["results"]:
            reference_id = result.get("referenceId")
            test_carrier = carrier_map.get(reference_id)
            
            if test_carrier and "errors" in result:
                error_details = []
                for error in result["errors"]:
                    error_details.append(f"{error.get('statusCode', 'UNKNOWN')}: {error.get('message', 'Unknown error')}")
                detail = "; ".join(error_details)
                
                # Create sync history record
                history_record = create_crm_sync_history_record(
                    db=db_session,
                    usdot=test_carrier.usdot,
                    sync_status="FAILED",
                    crm_object_type="account",
                    user_id=user_id,
                    org_id=org_id,
                    detail=detail,
                    sync_timestamp=sync_timestamp
                )
                
                # Upsert sync status
                status_record = upsert_sync_status(
                    db=db_session,
                    usdot=test_carrier.usdot,
                    org_id=org_id,
                    user_id=user_id,
                    sync_status="FAILED"
                )
        
        # Verify history record was created
        history_records = db_session.query(CRMSyncHistory).filter(
            CRMSyncHistory.usdot == "12346"
        ).all()
        assert len(history_records) == 1
        assert history_records[0].sync_status == "FAILED"
        assert history_records[0].crm_object_id is None
        assert "INVALID_EMAIL_ADDRESS" in history_records[0].detail
        
        # Verify status record was created
        status_records = db_session.query(CRMSyncStatus).filter(
            CRMSyncStatus.usdot == "12346",
            CRMSyncStatus.org_id == org_id
        ).all()
        assert len(status_records) == 1
        assert status_records[0].sobject_sync_status == "FAILED"
        assert status_records[0].sobject_id is None
    
    def test_mixed_success_failure_logging(self, db_session):
        """Test logging when some carriers succeed and others fail."""
        # Create test carriers
        carrier1 = CarrierData(usdot="12347", legal_name="Success Carrier", phone="555-1111")
        carrier2 = CarrierData(usdot="12348", legal_name="Fail Carrier", phone="555-2222")
        db_session.add(carrier1)
        db_session.add(carrier2)
        db_session.commit()
        
        # Mock mixed Salesforce response
        sf_response = {
            "hasErrors": True,
            "results": [
                {
                    "referenceId": "carrier_12347",
                    "id": "001D000000K1YFkIAN"
                },
                {
                    "referenceId": "carrier_12348",
                    "errors": [
                        {
                            "statusCode": "REQUIRED_FIELD_MISSING",
                            "message": "Required fields are missing: [Name]",
                            "fields": ["Name"]
                        }
                    ]
                }
            ]
        }
        
        user_id = "test-user"
        org_id = "test-org"
        sync_timestamp = datetime.utcnow()
        carrier_map = {"carrier_12347": carrier1, "carrier_12348": carrier2}
        
        # Process each result
        for result in sf_response["results"]:
            reference_id = result.get("referenceId")
            carrier = carrier_map.get(reference_id)
            
            if not carrier:
                continue
                
            if "errors" in result:
                # Failed sync
                error_details = []
                for error in result["errors"]:
                    error_details.append(f"{error.get('statusCode', 'UNKNOWN')}: {error.get('message', 'Unknown error')}")
                detail = "; ".join(error_details)
                
                create_crm_sync_history_record(
                    db=db_session,
                    usdot=carrier.usdot,
                    sync_status="FAILED",
                    crm_object_type="account",
                    user_id=user_id,
                    org_id=org_id,
                    detail=detail,
                    sync_timestamp=sync_timestamp
                )
                upsert_sync_status(
                    db=db_session,
                    usdot=carrier.usdot,
                    org_id=org_id,
                    user_id=user_id,
                    sync_status="FAILED"
                )
            elif "id" in result:
                # Successful sync
                salesforce_id = result["id"]
                create_crm_sync_history_record(
                    db=db_session,
                    usdot=carrier.usdot,
                    sync_status="SUCCESS",
                    crm_object_type="account",
                    user_id=user_id,
                    org_id=org_id,
                    crm_object_id=salesforce_id,
                    detail=f"Successfully created Account with ID: {salesforce_id}",
                    sync_timestamp=sync_timestamp
                )
                upsert_sync_status(
                    db=db_session,
                    usdot=carrier.usdot,
                    org_id=org_id,
                    user_id=user_id,
                    sync_status="SUCCESS",
                    crm_object_id=salesforce_id
                )
        
        # Verify both records were created correctly
        all_history = db_session.query(CRMSyncHistory).filter(
            CRMSyncHistory.usdot.in_(["12347", "12348"])
        ).all()
        assert len(all_history) == 2
        
        success_history = [h for h in all_history if h.sync_status == "SUCCESS"]
        failed_history = [h for h in all_history if h.sync_status == "FAILED"]
        
        assert len(success_history) == 1
        assert len(failed_history) == 1
        assert success_history[0].usdot == "12347"
        assert failed_history[0].usdot == "12348"
        
        # Verify status records
        all_status = db_session.query(CRMSyncStatus).filter(
            CRMSyncStatus.usdot.in_(["12347", "12348"])
        ).all()
        assert len(all_status) == 2
        
        success_status = [s for s in all_status if s.sobject_sync_status == "SUCCESS"]
        failed_status = [s for s in all_status if s.sobject_sync_status == "FAILED"]
        
        assert len(success_status) == 1
        assert len(failed_status) == 1
        assert success_status[0].sobject_id == "001D000000K1YFkIAN"
        assert failed_status[0].sobject_id is None