"""
Comprehensive tests for CRMSyncStatus functionality covering all scenarios
mentioned in the issue requirements.
"""
import pytest
import time
from sqlmodel import Session, create_engine, SQLModel
from app.crud.carrier_data import save_carrier_data_bulk, get_carrier_data
from app.crud.sobject_sync_status import get_sync_status_by_org, get_usdots_by_org
from app.models.carrier_data import CarrierDataCreate, CarrierData
from app.models.sobject_sync_status import CRMSyncStatus
from datetime import datetime


@pytest.fixture
def db_session():
    """Create a temporary in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_carrier_data():
    """Sample carrier data for testing."""
    return [
        CarrierDataCreate(
            usdot="123456",
            legal_name="Test Carrier 1",
            phone="555-0001",
            lookup_success_flag=True
        ),
        CarrierDataCreate(
            usdot="789012",
            legal_name="Test Carrier 2", 
            phone="555-0002",
            lookup_success_flag=True
        ),
        CarrierDataCreate(
            usdot="345678",
            legal_name="Test Carrier 3",
            phone="555-0003",
            lookup_success_flag=True
        )
    ]


class TestSameOrgScenarios:
    """Test scenarios where users from the same org interact with carriers."""
    
    def test_two_users_same_org_create_new_carriers(self, db_session, sample_carrier_data):
        """Test when two users of the same org_id create new carriers."""
        org_id = "org_alpha"
        user1_id = "user1_alpha"
        user2_id = "user2_alpha"
        
        # User 1 creates the first carrier
        user1_data = [sample_carrier_data[0]]
        result1 = save_carrier_data_bulk(db_session, user1_data, user1_id, org_id)
        
        # User 2 creates the second carrier
        user2_data = [sample_carrier_data[1]]
        result2 = save_carrier_data_bulk(db_session, user2_data, user2_id, org_id)
        
        # Verify both carriers were created
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0].usdot == "123456"
        assert result2[0].usdot == "789012"
        
        # Verify CRMSyncStatus records were created for the org
        sync_statuses = get_sync_status_by_org(db_session, org_id)
        assert len(sync_statuses) == 2
        
        # Verify org can access both carriers
        carriers = get_carrier_data(db_session, org_id=org_id)
        assert len(carriers) == 2
        carrier_usdots = {c.usdot for c in carriers}
        assert carrier_usdots == {"123456", "789012"}
        
        # Verify each record has correct user tracking
        status_by_usdot = {s.usdot: s for s in sync_statuses}
        assert status_by_usdot["123456"].user_id == user1_id
        assert status_by_usdot["789012"].user_id == user2_id
        assert status_by_usdot["123456"].org_id == org_id
        assert status_by_usdot["789012"].org_id == org_id
    
    def test_two_users_same_org_update_existing_carriers(self, db_session, sample_carrier_data):
        """Test when two users of the same org_id update existing carriers."""
        org_id = "org_beta"
        user1_id = "user1_beta"
        user2_id = "user2_beta"
        
        # Initial creation by user1
        initial_data = sample_carrier_data[:2]  # First two carriers
        save_carrier_data_bulk(db_session, initial_data, user1_id, org_id)
        
        # Get initial sync status timestamps
        initial_statuses = get_sync_status_by_org(db_session, org_id)
        initial_timestamps = {s.usdot: s.updated_at for s in initial_statuses}
        
        # User1 updates carrier 1
        updated_data1 = CarrierDataCreate(
            usdot="123456",
            legal_name="Updated Carrier 1",
            phone="555-1111",
            lookup_success_flag=True
        )
        save_carrier_data_bulk(db_session, [updated_data1], user1_id, org_id)
        
        # User2 updates carrier 2
        updated_data2 = CarrierDataCreate(
            usdot="789012",
            legal_name="Updated Carrier 2", 
            phone="555-2222",
            lookup_success_flag=True
        )
        save_carrier_data_bulk(db_session, [updated_data2], user2_id, org_id)
        
        # Verify carriers were updated
        carriers = get_carrier_data(db_session, org_id=org_id)
        carrier_by_usdot = {c.usdot: c for c in carriers}
        assert carrier_by_usdot["123456"].legal_name == "Updated Carrier 1"
        assert carrier_by_usdot["789012"].legal_name == "Updated Carrier 2"
        
        # Verify sync status records were updated with new timestamps and user info
        updated_statuses = get_sync_status_by_org(db_session, org_id)
        status_by_usdot = {s.usdot: s for s in updated_statuses}
        
        # Check timestamps were updated (should be newer than initial)
        assert status_by_usdot["123456"].updated_at > initial_timestamps["123456"]
        assert status_by_usdot["789012"].updated_at > initial_timestamps["789012"]
        
        # Check user tracking reflects the last user to update
        assert status_by_usdot["123456"].user_id == user1_id
        assert status_by_usdot["789012"].user_id == user2_id
    
    def test_same_org_one_creates_other_updates(self, db_session, sample_carrier_data):
        """Test when one user creates a carrier and another updates it (same org)."""
        org_id = "org_gamma"
        creator_id = "creator_gamma"
        updater_id = "updater_gamma"
        
        # Creator creates a carrier
        create_data = [sample_carrier_data[0]]
        save_carrier_data_bulk(db_session, create_data, creator_id, org_id)
        
        # Verify initial state
        initial_statuses = get_sync_status_by_org(db_session, org_id)
        initial_status = initial_statuses[0]
        initial_user_id = initial_status.user_id
        initial_updated_at = initial_status.updated_at
        assert initial_user_id == creator_id
        assert initial_status.usdot == "123456"
        
        # Small delay to ensure timestamp difference
        time.sleep(0.1)
        
        # Updater modifies the carrier
        update_data = CarrierDataCreate(
            usdot="123456",
            legal_name="Modified by Updater",
            phone="555-9999",
            lookup_success_flag=True
        )
        save_carrier_data_bulk(db_session, [update_data], updater_id, org_id)
        
        # Verify carrier was updated
        carriers = get_carrier_data(db_session, org_id=org_id)
        assert len(carriers) == 1
        assert carriers[0].legal_name == "Modified by Updater"
        
        # Verify sync status reflects the updater - get fresh data
        updated_statuses = get_sync_status_by_org(db_session, org_id)
        updated_status = updated_statuses[0]
        assert updated_status.user_id == updater_id
        assert updated_status.updated_at > initial_updated_at
        assert updated_status.org_id == org_id


class TestDifferentOrgScenarios:
    """Test scenarios where users from different orgs interact with carriers."""
    
    def test_two_users_different_orgs_create_new_carriers(self, db_session, sample_carrier_data):
        """Test when two users of different org_ids create new carriers."""
        org1_id = "org_delta"
        org2_id = "org_epsilon"
        user1_id = "user1_delta"
        user2_id = "user2_epsilon"
        
        # User from org1 creates carrier 1
        org1_data = [sample_carrier_data[0]]
        result1 = save_carrier_data_bulk(db_session, org1_data, user1_id, org1_id)
        
        # User from org2 creates carrier 2
        org2_data = [sample_carrier_data[1]]
        result2 = save_carrier_data_bulk(db_session, org2_data, user2_id, org2_id)
        
        # Verify carriers were created
        assert len(result1) == 1
        assert len(result2) == 1
        
        # Verify org isolation: each org only sees their own carriers
        org1_carriers = get_carrier_data(db_session, org_id=org1_id)
        org2_carriers = get_carrier_data(db_session, org_id=org2_id)
        
        assert len(org1_carriers) == 1
        assert len(org2_carriers) == 1
        assert org1_carriers[0].usdot == "123456"
        assert org2_carriers[0].usdot == "789012"
        
        # Verify sync status isolation
        org1_statuses = get_sync_status_by_org(db_session, org1_id)
        org2_statuses = get_sync_status_by_org(db_session, org2_id)
        
        assert len(org1_statuses) == 1
        assert len(org2_statuses) == 1
        assert org1_statuses[0].usdot == "123456"
        assert org2_statuses[0].usdot == "789012"
        assert org1_statuses[0].user_id == user1_id
        assert org2_statuses[0].user_id == user2_id
    
    def test_two_users_different_orgs_update_existing_carriers(self, db_session, sample_carrier_data):
        """Test when two users of different org_ids update existing carriers."""
        org1_id = "org_zeta"
        org2_id = "org_eta"
        user1_id = "user1_zeta"
        user2_id = "user2_eta"
        
        # Both orgs create their own carriers initially
        save_carrier_data_bulk(db_session, [sample_carrier_data[0]], user1_id, org1_id)
        save_carrier_data_bulk(db_session, [sample_carrier_data[1]], user2_id, org2_id)
        
        # Each org updates their carrier
        updated_data1 = CarrierDataCreate(
            usdot="123456",
            legal_name="Org1 Updated Carrier",
            phone="555-1001",
            lookup_success_flag=True
        )
        updated_data2 = CarrierDataCreate(
            usdot="789012",
            legal_name="Org2 Updated Carrier",
            phone="555-2002",
            lookup_success_flag=True
        )
        
        save_carrier_data_bulk(db_session, [updated_data1], user1_id, org1_id)
        save_carrier_data_bulk(db_session, [updated_data2], user2_id, org2_id)
        
        # Verify each org still only sees their own updated carrier
        org1_carriers = get_carrier_data(db_session, org_id=org1_id)
        org2_carriers = get_carrier_data(db_session, org_id=org2_id)
        
        assert len(org1_carriers) == 1
        assert len(org2_carriers) == 1
        assert org1_carriers[0].legal_name == "Org1 Updated Carrier"
        assert org2_carriers[0].legal_name == "Org2 Updated Carrier"
        
        # Verify sync status records are separate
        org1_statuses = get_sync_status_by_org(db_session, org1_id)
        org2_statuses = get_sync_status_by_org(db_session, org2_id)
        
        assert len(org1_statuses) == 1
        assert len(org2_statuses) == 1
        assert org1_statuses[0].user_id == user1_id
        assert org2_statuses[0].user_id == user2_id
    
    def test_different_orgs_one_creates_other_updates(self, db_session, sample_carrier_data):
        """Test when one user creates a carrier and user from different org updates same USDOT."""
        org1_id = "org_theta"
        org2_id = "org_iota"
        user1_id = "user1_theta"
        user2_id = "user2_iota"
        
        # User from org1 creates a carrier
        create_data = [sample_carrier_data[0]]
        save_carrier_data_bulk(db_session, create_data, user1_id, org1_id)
        
        # User from org2 "creates" (but actually updates) the same USDOT carrier
        update_data = CarrierDataCreate(
            usdot="123456",  # Same USDOT
            legal_name="Org2 Version of Carrier",
            phone="555-3333",
            lookup_success_flag=True
        )
        save_carrier_data_bulk(db_session, [update_data], user2_id, org2_id)
        
        # Verify the carrier data was updated (since it's the same USDOT)
        # But each org has their own sync status record
        org1_carriers = get_carrier_data(db_session, org_id=org1_id)
        org2_carriers = get_carrier_data(db_session, org_id=org2_id)
        
        assert len(org1_carriers) == 1
        assert len(org2_carriers) == 1
        
        # Both should see the updated carrier data (since same USDOT)
        assert org1_carriers[0].legal_name == "Org2 Version of Carrier"
        assert org2_carriers[0].legal_name == "Org2 Version of Carrier"
        
        # But they should have separate sync status records
        org1_statuses = get_sync_status_by_org(db_session, org1_id)
        org2_statuses = get_sync_status_by_org(db_session, org2_id)
        
        assert len(org1_statuses) == 1
        assert len(org2_statuses) == 1
        assert org1_statuses[0].usdot == "123456"
        assert org2_statuses[0].usdot == "123456"
        assert org1_statuses[0].user_id == user1_id  # Original creator
        assert org2_statuses[0].user_id == user2_id  # Second org user


class TestCRMSyncStatusBehavior:
    """Test specific CRMSyncStatus functionality."""
    
    def test_sync_status_defaults_to_pending(self, db_session, sample_carrier_data):
        """Test that new carrier registrations default to PENDING sync status."""
        org_id = "org_test"
        user_id = "user_test"
        
        save_carrier_data_bulk(db_session, [sample_carrier_data[0]], user_id, org_id)
        
        statuses = get_sync_status_by_org(db_session, org_id)
        assert len(statuses) == 1
        assert statuses[0].sobject_sync_status == "PENDING"
        assert statuses[0].sobject_id is None
        assert statuses[0].sobject_synced_at is None
    
    def test_get_usdots_by_org_functionality(self, db_session, sample_carrier_data):
        """Test the new get_usdots_by_org function."""
        org_id = "org_lookup"
        user_id = "user_lookup"
        
        # Create multiple carriers for the org
        save_carrier_data_bulk(db_session, sample_carrier_data, user_id, org_id)
        
        usdots = get_usdots_by_org(db_session, org_id)
        assert len(usdots) == 3
        assert set(usdots) == {"123456", "789012", "345678"}
        
        # Verify get_carrier_data uses this function correctly
        carriers = get_carrier_data(db_session, org_id=org_id)
        carrier_usdots = {c.usdot for c in carriers}
        assert carrier_usdots == set(usdots)
    
    def test_timestamps_behavior(self, db_session, sample_carrier_data):
        """Test created_at and updated_at timestamp behavior."""
        org_id = "org_time"
        user_id = "user_time"
        
        # Create carrier
        before_create = datetime.utcnow()
        save_carrier_data_bulk(db_session, [sample_carrier_data[0]], user_id, org_id)
        after_create = datetime.utcnow()
        
        initial_statuses = get_sync_status_by_org(db_session, org_id)
        status = initial_statuses[0]
        initial_created_at = status.created_at
        initial_updated_at = status.updated_at
        
        # Verify timestamps are within expected range
        assert before_create <= initial_created_at <= after_create
        assert before_create <= initial_updated_at <= after_create
        # Allow for small timing differences
        assert abs((initial_created_at - initial_updated_at).total_seconds()) < 0.1
        
        # Small delay to ensure timestamp difference
        time.sleep(0.1)
        
        # Update the carrier
        updated_data = CarrierDataCreate(
            usdot="123456",
            legal_name="Updated Carrier",
            phone="555-4444",
            lookup_success_flag=True
        )
        
        before_update = datetime.utcnow()
        save_carrier_data_bulk(db_session, [updated_data], user_id, org_id)
        after_update = datetime.utcnow()
        
        # Get fresh data
        updated_statuses = get_sync_status_by_org(db_session, org_id)
        updated_status = updated_statuses[0]
        
        # Verify created_at stayed the same but updated_at changed
        assert updated_status.created_at == initial_created_at
        assert before_update <= updated_status.updated_at <= after_update
        assert updated_status.updated_at > initial_updated_at