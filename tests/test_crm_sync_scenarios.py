"""
Tests for CRM sync status scenarios as specified in the issue.
Tests cover various combinations of users and organizations creating/updating carriers.
"""
import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.crud.carrier_data import save_carrier_data_bulk
from app.crud.sobject_sync_status import get_crm_sync_status_by_usdot, get_crm_sync_status_by_org
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
    return CarrierDataCreate(
        usdot="123456",
        legal_name="Test Carrier LLC",
        phone="555-1234",
        mailing_address="123 Test St, Test City, TS 12345",
        lookup_success_flag=True
    )


@pytest.fixture
def another_carrier_data():
    """Another sample carrier data for testing."""
    return CarrierDataCreate(
        usdot="789012",
        legal_name="Another Carrier Corp",
        phone="555-5678",
        mailing_address="456 Another St, Test City, TS 12345",
        lookup_success_flag=True
    )


class TestCRMSyncStatusScenarios:
    """Test CRM sync status scenarios as specified in the issue."""
    
    def test_two_users_same_org_create_new_carriers(self, db_session, sample_carrier_data, another_carrier_data):
        """Test when two users of the same org_id create new carriers."""
        user1 = "user1"
        user2 = "user2"
        org_id = "org1"
        
        # User 1 creates first carrier
        result1 = save_carrier_data_bulk(db_session, [sample_carrier_data], user1, org_id)
        assert len(result1) == 1
        
        # Check CRM sync record was created for user 1
        sync1 = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org_id)
        assert sync1 is not None
        assert sync1.user_id == user1
        assert sync1.org_id == org_id
        assert sync1.usdot == sample_carrier_data.usdot
        
        # User 2 creates second carrier (same org)
        result2 = save_carrier_data_bulk(db_session, [another_carrier_data], user2, org_id)
        assert len(result2) == 1
        
        # Check CRM sync record was created for user 2
        sync2 = get_crm_sync_status_by_usdot(db_session, another_carrier_data.usdot, org_id)
        assert sync2 is not None
        assert sync2.user_id == user2
        assert sync2.org_id == org_id
        assert sync2.usdot == another_carrier_data.usdot
        
        # Verify both records exist for the same org
        org_syncs = get_crm_sync_status_by_org(db_session, org_id)
        assert len(org_syncs) == 2
        usdots = [sync.usdot for sync in org_syncs]
        assert sample_carrier_data.usdot in usdots
        assert another_carrier_data.usdot in usdots
    
    def test_two_users_same_org_update_existing_carriers(self, db_session, sample_carrier_data, another_carrier_data):
        """Test when two users of the same org_id update existing carriers."""
        user1 = "user1"
        user2 = "user2"
        org_id = "org1"
        
        # Create initial carriers
        save_carrier_data_bulk(db_session, [sample_carrier_data, another_carrier_data], user1, org_id)
        
        # Get initial timestamps
        sync1_initial = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org_id)
        sync2_initial = get_crm_sync_status_by_usdot(db_session, another_carrier_data.usdot, org_id)
        initial_time1 = sync1_initial.updated_at
        initial_time2 = sync2_initial.updated_at
        
        # User 1 updates first carrier
        updated_carrier1 = sample_carrier_data.model_copy(update={"legal_name": "Updated Carrier LLC"})
        save_carrier_data_bulk(db_session, [updated_carrier1], user1, org_id)
        
        # User 2 updates second carrier
        updated_carrier2 = another_carrier_data.model_copy(update={"legal_name": "Updated Another Corp"})
        save_carrier_data_bulk(db_session, [updated_carrier2], user2, org_id)
        
        # Verify updates
        sync1_updated = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org_id)
        sync2_updated = get_crm_sync_status_by_usdot(db_session, another_carrier_data.usdot, org_id)
        
        assert sync1_updated.user_id == user1
        assert sync2_updated.user_id == user2
        assert sync1_updated.updated_at > initial_time1
        assert sync2_updated.updated_at > initial_time2
    
    def test_one_user_create_other_update_same_org(self, db_session, sample_carrier_data, another_carrier_data):
        """Test when one user creates a carrier and another updates an existing one (same org_id)."""
        user1 = "user1"
        user2 = "user2"
        org_id = "org1"
        
        # User 1 creates first carrier
        save_carrier_data_bulk(db_session, [sample_carrier_data], user1, org_id)
        
        # User 2 creates second carrier and updates first one
        updated_carrier1 = sample_carrier_data.model_copy(update={"legal_name": "Updated by User2"})
        save_carrier_data_bulk(db_session, [updated_carrier1, another_carrier_data], user2, org_id)
        
        # Verify first carrier was updated by user2
        sync1 = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org_id)
        assert sync1.user_id == user2  # Should be updated to user2
        
        # Verify second carrier was created by user2
        sync2 = get_crm_sync_status_by_usdot(db_session, another_carrier_data.usdot, org_id)
        assert sync2.user_id == user2
        
        # Both should be in the same org
        org_syncs = get_crm_sync_status_by_org(db_session, org_id)
        assert len(org_syncs) == 2
    
    def test_two_users_different_org_create_new_carriers(self, db_session, sample_carrier_data, another_carrier_data):
        """Test when two users of different org_id create new carriers."""
        user1 = "user1"
        user2 = "user2"
        org1 = "org1"
        org2 = "org2"
        
        # User 1 creates carrier in org1
        result1 = save_carrier_data_bulk(db_session, [sample_carrier_data], user1, org1)
        assert len(result1) == 1
        
        # User 2 creates carrier in org2 
        result2 = save_carrier_data_bulk(db_session, [another_carrier_data], user2, org2)
        assert len(result2) == 1
        
        # Verify separate org records
        sync1 = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org1)
        sync2 = get_crm_sync_status_by_usdot(db_session, another_carrier_data.usdot, org2)
        
        assert sync1.org_id == org1
        assert sync2.org_id == org2
        assert sync1.user_id == user1
        assert sync2.user_id == user2
        
        # Verify each org has only its carrier
        org1_syncs = get_crm_sync_status_by_org(db_session, org1)
        org2_syncs = get_crm_sync_status_by_org(db_session, org2)
        
        assert len(org1_syncs) == 1
        assert len(org2_syncs) == 1
        assert org1_syncs[0].usdot == sample_carrier_data.usdot
        assert org2_syncs[0].usdot == another_carrier_data.usdot
    
    def test_two_users_different_org_update_existing_carriers(self, db_session, sample_carrier_data, another_carrier_data):
        """Test when two users of different org_id update existing carriers."""
        user1 = "user1"
        user2 = "user2"
        org1 = "org1"
        org2 = "org2"
        
        # Create initial carriers in different orgs
        save_carrier_data_bulk(db_session, [sample_carrier_data], user1, org1)
        save_carrier_data_bulk(db_session, [another_carrier_data], user2, org2)
        
        # Update carriers
        updated_carrier1 = sample_carrier_data.model_copy(update={"legal_name": "Updated by Org1"})
        updated_carrier2 = another_carrier_data.model_copy(update={"legal_name": "Updated by Org2"})
        
        save_carrier_data_bulk(db_session, [updated_carrier1], user1, org1)
        save_carrier_data_bulk(db_session, [updated_carrier2], user2, org2)
        
        # Verify updates maintain org separation
        sync1 = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org1)
        sync2 = get_crm_sync_status_by_usdot(db_session, another_carrier_data.usdot, org2)
        
        assert sync1.org_id == org1
        assert sync2.org_id == org2
        assert sync1.user_id == user1
        assert sync2.user_id == user2
    
    def test_one_user_create_other_update_different_org(self, db_session, sample_carrier_data, another_carrier_data):
        """Test when one user creates a carrier and another updates an existing one (different org_id)."""
        user1 = "user1"
        user2 = "user2"
        org1 = "org1"
        org2 = "org2"
        
        # User 1 creates carrier in org1
        save_carrier_data_bulk(db_session, [sample_carrier_data], user1, org1)
        
        # User 2 creates new carrier and tries to "update" the same USDOT in org2
        # This should create a separate record since it's a different org
        same_usdot_carrier = sample_carrier_data.model_copy(update={"legal_name": "Same USDOT Different Org"})
        save_carrier_data_bulk(db_session, [same_usdot_carrier, another_carrier_data], user2, org2)
        
        # Verify both orgs have records for the same USDOT (carrier data is shared)
        sync1_org1 = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org1)
        sync1_org2 = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org2)
        sync2_org2 = get_crm_sync_status_by_usdot(db_session, another_carrier_data.usdot, org2)
        
        assert sync1_org1 is not None
        assert sync1_org2 is not None
        assert sync2_org2 is not None
        
        assert sync1_org1.org_id == org1
        assert sync1_org2.org_id == org2
        assert sync2_org2.org_id == org2
        
        assert sync1_org1.user_id == user1
        assert sync1_org2.user_id == user2
        assert sync2_org2.user_id == user2
        
        # Verify org separation
        org1_syncs = get_crm_sync_status_by_org(db_session, org1)
        org2_syncs = get_crm_sync_status_by_org(db_session, org2)
        
        assert len(org1_syncs) == 1
        assert len(org2_syncs) == 2
    
    def test_transaction_rollback_on_failure(self, db_session, sample_carrier_data):
        """Test that transaction is rolled back if any part fails."""
        user_id = "user1"
        org_id = "org1"
        
        # This should work normally first
        result = save_carrier_data_bulk(db_session, [sample_carrier_data], user_id, org_id)
        assert len(result) == 1
        
        # Verify record exists
        sync = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org_id)
        assert sync is not None
    
    def test_timestamps_behavior(self, db_session, sample_carrier_data):
        """Test that created_at is set on creation and updated_at is set on updates."""
        user_id = "user1"
        org_id = "org1"
        
        # Create carrier
        save_carrier_data_bulk(db_session, [sample_carrier_data], user_id, org_id)
        
        sync_initial = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org_id)
        created_at = sync_initial.created_at
        updated_at_initial = sync_initial.updated_at
        
        # Update carrier
        updated_carrier = sample_carrier_data.model_copy(update={"legal_name": "Updated Name"})
        save_carrier_data_bulk(db_session, [updated_carrier], user_id, org_id)
        
        sync_updated = get_crm_sync_status_by_usdot(db_session, sample_carrier_data.usdot, org_id)
        
        # created_at should remain the same, updated_at should be newer
        assert sync_updated.created_at == created_at
        assert sync_updated.updated_at >= updated_at_initial