"""
Test configuration and fixtures for the USDOT Lookup Tool tests.
"""
import pytest
import os
from unittest.mock import Mock, MagicMock
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime
from typing import Generator

# Set environment variables for tests
os.environ.setdefault('DB_USER', 'test_user')
os.environ.setdefault('DB_PASSWORD', 'test_password')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_NAME', 'test_db')
os.environ.setdefault('WEBAPP_SESSION_SECRET', 'test_secret')
os.environ.setdefault('AUTH0_DOMAIN', 'test.auth0.com')
os.environ.setdefault('AUTH0_CLIENT_ID', 'test_client_id')
os.environ.setdefault('GCP_OCR_API_KEY', 'test_api_key')
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', '/tmp/fake_credentials.json')

# Import models and schemas after setting env vars
from app.models.carrier_data import CarrierData, CarrierDataCreate
from app.models.engagement import CarrierEngagementStatus, CarrierChangeItem
from app.models.ocr_results import OCRResult, OCRResultCreate
from app.models.user_org_membership import AppUser, AppOrg


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    
    # Add common mock behaviors
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    session.commit.return_value = None
    session.rollback.return_value = None
    session.refresh.return_value = None
    session.add.return_value = None
    session.add_all.return_value = None
    
    return session


@pytest.fixture
def sample_carrier_data():
    """Create sample carrier data for testing."""
    return CarrierDataCreate(
        usdot="123456",
        legal_name="Test Carrier LLC",
        dba_name="Test Carrier",
        physical_address="123 Test St, Test City, TS 12345",
        mailing_address="PO Box 123, Test City, TS 12345", 
        phone="555-123-4567",
        entity_type="LLC",
        usdot_status="ACTIVE",
        power_units=10,
        drivers=5,
        operation_classification="Interstate",
        carrier_operation="Motor Carrier",
        lookup_success_flag=True
    )


@pytest.fixture
def sample_carrier_db_record():
    """Create sample carrier database record for testing."""
    return CarrierData(
        usdot="123456",
        legal_name="Test Carrier LLC",
        dba_name="Test Carrier",
        physical_address="123 Test St, Test City, TS 12345",
        mailing_address="PO Box 123, Test City, TS 12345",
        phone="555-123-4567",
        entity_type="LLC",
        usdot_status="ACTIVE",
        power_units=10,
        drivers=5,
        operation_classification="Interstate",
        carrier_operation="Motor Carrier"
    )


@pytest.fixture 
def sample_ocr_result():
    """Create sample OCR result for testing."""
    return OCRResultCreate(
        extracted_text="USDOT 123456 TEST CARRIER LLC",
        filename="test_image.jpg",
        user_id="test_user_123",
        org_id="test_org_456"
    )


@pytest.fixture
def sample_ocr_db_record():
    """Create sample OCR database record for testing."""
    return OCRResult(
        id=1,
        extracted_text="USDOT 123456 TEST CARRIER LLC",
        dot_reading="123456",
        filename="test_image.jpg",
        timestamp=datetime.utcnow(),
        user_id="test_user_123",
        org_id="test_org_456"
    )


@pytest.fixture
def sample_engagement_record():
    """Create sample engagement record for testing."""
    return CarrierEngagementStatus(
        usdot="123456",
        org_id="test_org_456", 
        user_id="test_user_123",
        created_at=datetime.utcnow(),
        carrier_interested=False,
        carrier_contacted=False,
        carrier_followed_up=False,
        carrier_emailed=False
    )


@pytest.fixture
def sample_change_item():
    """Create sample change item for testing."""
    return CarrierChangeItem(
        usdot="123456",
        field="carrier_interested",
        value=True
    )


@pytest.fixture  
def mock_request():
    """Create a mock FastAPI request object."""
    request = Mock()
    request.session = {
        'userinfo': {
            'sub': 'test_user_123',
            'org_id': 'test_org_456'
        }
    }
    return request


@pytest.fixture
def mock_file_upload():
    """Create a mock file upload for testing."""
    mock_file = Mock()
    mock_file.filename = "test_image.jpg"
    mock_file.read.return_value = b"fake_image_data"
    mock_file.content_type = "image/jpeg"
    return mock_file


@pytest.fixture
def test_client():
    """Create a test client for FastAPI testing (when needed)."""
    # Note: This would need environment variables set for full testing
    # For now, we'll mock the app components individually
    pass


# Add fixtures for auth testing
@pytest.fixture
def mock_auth_session():
    """Create a mock authenticated session."""
    return {
        'id_token': 'mock_token',
        'userinfo': {
            'sub': 'test_user_123',
            'email': 'test@example.com',
            'org_id': 'test_org_456'
        }
    }


@pytest.fixture  
def mock_unauthenticated_session():
    """Create a mock unauthenticated session."""
    return {}