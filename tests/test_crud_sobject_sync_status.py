import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.crud.sobject_sync_status import (
    upsert_sync_status,
    get_sync_status_by_usdot,
    get_sync_status_by_org,
    get_sync_status_for_usdots,
    delete_sync_status
)
from app.models.sobject_sync_status import SObjectSyncStatus
from datetime import datetime


@pytest.fixture
def db_session():
    """Create a temporary in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestUpsertSyncStatus:
    """Test cases for upserting sync status records."""
    
    def test_upsert_sync_status_new_record(self, db_session):
        """Test creating a new sync status record."""
        result = upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS",
            sobject_id="sf001"
        )
        
        assert result.usdot == "12345"
        assert result.org_id == "org1"
        assert result.user_id == "user1"
        assert result.sync_status == "SUCCESS"
        assert result.sobject_id == "sf001"
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)
    
    def test_upsert_sync_status_update_existing(self, db_session):
        """Test updating an existing sync status record."""
        # Create initial record
        initial = upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="FAILED"
        )
        initial_created_at = initial.created_at
        
        # Update the record
        updated = upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user2",
            sync_status="SUCCESS",
            sobject_id="sf001"
        )
        
        assert updated.usdot == "12345"
        assert updated.org_id == "org1"
        assert updated.user_id == "user2"  # Should be updated
        assert updated.sync_status == "SUCCESS"  # Should be updated
        assert updated.sobject_id == "sf001"  # Should be updated
        assert updated.created_at == initial_created_at  # Should remain the same
        assert updated.updated_at > initial_created_at  # Should be newer
    
    def test_upsert_sync_status_different_orgs(self, db_session):
        """Test that records with same USDOT but different orgs are separate."""
        result1 = upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS"
        )
        
        result2 = upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org2",
            user_id="user2",
            sync_status="FAILED"
        )
        
        assert result1.org_id == "org1"
        assert result2.org_id == "org2"
        assert result1.sync_status == "SUCCESS"
        assert result2.sync_status == "FAILED"


class TestGetSyncStatusByUsdot:
    """Test cases for getting sync status by USDOT and org."""
    
    def test_get_sync_status_by_usdot_found(self, db_session):
        """Test retrieving existing sync status."""
        upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS",
            sobject_id="sf001"
        )
        
        result = get_sync_status_by_usdot(db_session, "12345", "org1")
        
        assert result is not None
        assert result.usdot == "12345"
        assert result.org_id == "org1"
        assert result.sync_status == "SUCCESS"
        assert result.sobject_id == "sf001"
    
    def test_get_sync_status_by_usdot_not_found(self, db_session):
        """Test retrieving non-existent sync status."""
        result = get_sync_status_by_usdot(db_session, "99999", "org1")
        assert result is None
    
    def test_get_sync_status_by_usdot_wrong_org(self, db_session):
        """Test retrieving sync status with wrong org."""
        upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS"
        )
        
        result = get_sync_status_by_usdot(db_session, "12345", "org2")
        assert result is None


class TestGetSyncStatusByOrg:
    """Test cases for getting sync status by org."""
    
    def test_get_sync_status_by_org_all(self, db_session):
        """Test retrieving all sync status records for an org."""
        upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS"
        )
        upsert_sync_status(
            db=db_session,
            usdot="12346",
            org_id="org1",
            user_id="user2",
            sync_status="FAILED"
        )
        upsert_sync_status(
            db=db_session,
            usdot="12347",
            org_id="org2",
            user_id="user3",
            sync_status="SUCCESS"
        )
        
        results = get_sync_status_by_org(db_session, "org1")
        
        assert len(results) == 2
        assert all(record.org_id == "org1" for record in results)
        usdots = [record.usdot for record in results]
        assert "12345" in usdots
        assert "12346" in usdots
        assert "12347" not in usdots
    
    def test_get_sync_status_by_org_filtered_by_status(self, db_session):
        """Test retrieving sync status filtered by status."""
        upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS"
        )
        upsert_sync_status(
            db=db_session,
            usdot="12346",
            org_id="org1",
            user_id="user2",
            sync_status="FAILED"
        )
        
        successful_results = get_sync_status_by_org(db_session, "org1", sync_status="SUCCESS")
        failed_results = get_sync_status_by_org(db_session, "org1", sync_status="FAILED")
        
        assert len(successful_results) == 1
        assert successful_results[0].usdot == "12345"
        assert len(failed_results) == 1
        assert failed_results[0].usdot == "12346"


class TestGetSyncStatusForUsdots:
    """Test cases for getting sync status for multiple USDOTs."""
    
    def test_get_sync_status_for_usdots_all_found(self, db_session):
        """Test retrieving sync status for multiple USDOTs when all exist."""
        usdots = ["12345", "12346", "12347"]
        
        for usdot in usdots:
            upsert_sync_status(
                db=db_session,
                usdot=usdot,
                org_id="org1",
                user_id="user1",
                sync_status="SUCCESS"
            )
        
        results = get_sync_status_for_usdots(db_session, usdots, "org1")
        
        assert len(results) == 3
        assert set(results.keys()) == set(usdots)
        assert all(record.org_id == "org1" for record in results.values())
    
    def test_get_sync_status_for_usdots_partial_found(self, db_session):
        """Test retrieving sync status when only some USDOTs exist."""
        upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS"
        )
        
        usdots = ["12345", "12346", "12347"]
        results = get_sync_status_for_usdots(db_session, usdots, "org1")
        
        assert len(results) == 1
        assert "12345" in results
        assert "12346" not in results
        assert "12347" not in results
    
    def test_get_sync_status_for_usdots_none_found(self, db_session):
        """Test retrieving sync status when no USDOTs exist."""
        usdots = ["99999", "99998", "99997"]
        results = get_sync_status_for_usdots(db_session, usdots, "org1")
        
        assert len(results) == 0
        assert results == {}


class TestDeleteSyncStatus:
    """Test cases for deleting sync status records."""
    
    def test_delete_sync_status_success(self, db_session):
        """Test successful deletion of sync status."""
        upsert_sync_status(
            db=db_session,
            usdot="12345",
            org_id="org1",
            user_id="user1",
            sync_status="SUCCESS"
        )
        
        # Verify it exists
        assert get_sync_status_by_usdot(db_session, "12345", "org1") is not None
        
        # Delete it
        result = delete_sync_status(db_session, "12345", "org1")
        assert result is True
        
        # Verify it's gone
        assert get_sync_status_by_usdot(db_session, "12345", "org1") is None
    
    def test_delete_sync_status_not_found(self, db_session):
        """Test deletion of non-existent sync status."""
        result = delete_sync_status(db_session, "99999", "org1")
        assert result is False