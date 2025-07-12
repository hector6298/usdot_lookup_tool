import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.crud.sobject_sync_history import (
    create_sync_history_record,
    get_sync_history_by_usdot,
    get_sync_history_by_org
)
from app.models.sobject_sync_history import SObjectSyncHistory
from datetime import datetime, timedelta


@pytest.fixture
def db_session():
    """Create a temporary in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestCreateSyncHistoryRecord:
    """Test cases for creating sync history records."""
    
    def test_create_sync_history_record_success(self, db_session):
        """Test successful creation of sync history record."""
        result = create_sync_history_record(
            db=db_session,
            usdot="12345",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user1",
            org_id="org1",
            sobject_id="sf001",
            detail="Successfully created account"
        )
        
        assert result.id is not None
        assert result.usdot == "12345"
        assert result.sync_status == "SUCCESS"
        assert result.sobject_type == "account"
        assert result.user_id == "user1"
        assert result.org_id == "org1"
        assert result.sobject_id == "sf001"
        assert result.detail == "Successfully created account"
        assert isinstance(result.sync_timestamp, datetime)
    
    def test_create_sync_history_record_failed(self, db_session):
        """Test creation of failed sync history record."""
        result = create_sync_history_record(
            db=db_session,
            usdot="12346",
            sync_status="FAILED",
            sobject_type="account",
            user_id="user1",
            org_id="org1",
            detail="INVALID_EMAIL_ADDRESS: Email: invalid email address: 123"
        )
        
        assert result.usdot == "12346"
        assert result.sync_status == "FAILED"
        assert result.sobject_id is None
        assert "INVALID_EMAIL_ADDRESS" in result.detail
    
    def test_create_sync_history_record_custom_timestamp(self, db_session):
        """Test creation with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        
        result = create_sync_history_record(
            db=db_session,
            usdot="12347",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user1",
            org_id="org1",
            sync_timestamp=custom_time
        )
        
        assert result.sync_timestamp == custom_time


class TestGetSyncHistoryByUsdot:
    """Test cases for getting sync history by USDOT."""
    
    def test_get_sync_history_by_usdot_found(self, db_session):
        """Test retrieving sync history for existing USDOT."""
        # Create test records
        create_sync_history_record(
            db=db_session,
            usdot="12345",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user1",
            org_id="org1"
        )
        create_sync_history_record(
            db=db_session,
            usdot="12345",
            sync_status="FAILED",
            sobject_type="account",
            user_id="user1",
            org_id="org1"
        )
        
        results = get_sync_history_by_usdot(db_session, "12345")
        
        assert len(results) == 2
        assert all(record.usdot == "12345" for record in results)
        # Should be ordered by timestamp desc (most recent first)
        assert results[0].sync_timestamp >= results[1].sync_timestamp
    
    def test_get_sync_history_by_usdot_with_org_filter(self, db_session):
        """Test retrieving sync history filtered by org."""
        create_sync_history_record(
            db=db_session,
            usdot="12345",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user1",
            org_id="org1"
        )
        create_sync_history_record(
            db=db_session,
            usdot="12345",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user2",
            org_id="org2"
        )
        
        results = get_sync_history_by_usdot(db_session, "12345", org_id="org1")
        
        assert len(results) == 1
        assert results[0].org_id == "org1"
    
    def test_get_sync_history_by_usdot_not_found(self, db_session):
        """Test retrieving sync history for non-existent USDOT."""
        results = get_sync_history_by_usdot(db_session, "99999")
        assert len(results) == 0
    
    def test_get_sync_history_by_usdot_with_limit(self, db_session):
        """Test retrieving sync history with limit."""
        # Create 5 records
        for i in range(5):
            create_sync_history_record(
                db=db_session,
                usdot="12345",
                sync_status="SUCCESS",
                sobject_type="account",
                user_id="user1",
                org_id="org1"
            )
        
        results = get_sync_history_by_usdot(db_session, "12345", limit=3)
        assert len(results) == 3


class TestGetSyncHistoryByOrg:
    """Test cases for getting sync history by org."""
    
    def test_get_sync_history_by_org_found(self, db_session):
        """Test retrieving sync history for existing org."""
        create_sync_history_record(
            db=db_session,
            usdot="12345",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user1",
            org_id="org1"
        )
        create_sync_history_record(
            db=db_session,
            usdot="12346",
            sync_status="FAILED",
            sobject_type="account",
            user_id="user2",
            org_id="org1"
        )
        
        results = get_sync_history_by_org(db_session, "org1")
        
        assert len(results) == 2
        assert all(record.org_id == "org1" for record in results)
    
    def test_get_sync_history_by_org_with_user_filter(self, db_session):
        """Test retrieving sync history filtered by user."""
        create_sync_history_record(
            db=db_session,
            usdot="12345",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user1",
            org_id="org1"
        )
        create_sync_history_record(
            db=db_session,
            usdot="12346",
            sync_status="SUCCESS",
            sobject_type="account",
            user_id="user2",
            org_id="org1"
        )
        
        results = get_sync_history_by_org(db_session, "org1", user_id="user1")
        
        assert len(results) == 1
        assert results[0].user_id == "user1"
    
    def test_get_sync_history_by_org_not_found(self, db_session):
        """Test retrieving sync history for non-existent org."""
        results = get_sync_history_by_org(db_session, "nonexistent")
        assert len(results) == 0