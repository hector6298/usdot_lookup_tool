"""
Unit tests for OAuth CRUD operations.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.crud.oauth import (
    upsert_salesforce_token,
    get_valid_salesforce_token,
    delete_salesforce_token
)
from app.models.oauth import OAuthToken


class TestUpsertSalesforceToken:
    """Test upsert_salesforce_token function."""
    
    def test_upsert_salesforce_token_new_record(self, mock_db_session):
        """Test creating a new Salesforce token record."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        token_data = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'token_type': 'Bearer',
            'issued_at': '1609459200000'  # Timestamp in milliseconds
        }
        
        mock_db_session.exec.return_value.first.return_value = None  # No existing token
        
        # Act
        result = upsert_salesforce_token(mock_db_session, user_id, org_id, token_data)
        
        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    def test_upsert_salesforce_token_update_existing(self, mock_db_session):
        """Test updating an existing Salesforce token record."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        token_data = {
            'access_token': 'updated_access_token',
            'refresh_token': 'updated_refresh_token',
            'token_type': 'Bearer',
            'issued_at': '1609459200000'
        }
        
        existing_token = Mock(spec=OAuthToken)
        mock_db_session.exec.return_value.first.return_value = existing_token
        
        # Act
        result = upsert_salesforce_token(mock_db_session, user_id, org_id, token_data)
        
        # Assert
        assert result == existing_token
        assert existing_token.access_token == 'updated_access_token'
        assert existing_token.refresh_token == 'updated_refresh_token'
        assert existing_token.provider == 'salesforce'
        mock_db_session.add.assert_not_called()  # Should not add when updating
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(existing_token)
    
    def test_upsert_salesforce_token_calculates_expiry(self, mock_db_session):
        """Test that token expiry is calculated correctly."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        token_data = {
            'access_token': 'test_token',
            'issued_at': '1609459200000'  # Jan 1, 2021 00:00:00 UTC
        }
        
        existing_token = Mock(spec=OAuthToken)
        mock_db_session.exec.return_value.first.return_value = existing_token
        
        # Act
        result = upsert_salesforce_token(mock_db_session, user_id, org_id, token_data)
        
        # Assert
        expected_issued_at = datetime.fromtimestamp(1609459200)  # Convert to datetime
        expected_valid_until = expected_issued_at + timedelta(seconds=7200)  # 2 hours later
        
        assert existing_token.issued_at == expected_issued_at
        assert existing_token.valid_until == expected_valid_until
    
    def test_upsert_salesforce_token_missing_issued_at(self, mock_db_session):
        """Test handling when issued_at is missing from token data."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        token_data = {
            'access_token': 'test_token'
            # No issued_at provided
        }
        
        mock_db_session.exec.return_value.first.return_value = None
        
        # Act
        result = upsert_salesforce_token(mock_db_session, user_id, org_id, token_data)
        
        # Assert - should not fail, defaults to 0
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestGetValidSalesforceToken:
    """Test get_valid_salesforce_token function."""
    
    @pytest.mark.asyncio
    async def test_get_valid_salesforce_token_valid_token(self, mock_db_session):
        """Test getting a valid token that hasn't expired."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        valid_token = Mock(spec=OAuthToken)
        valid_token.access_token = "valid_access_token"
        valid_token.valid_until = datetime.utcnow() + timedelta(hours=1)  # Valid for 1 more hour
        
        mock_db_session.exec.return_value.first.return_value = valid_token
        
        # Act
        result = await get_valid_salesforce_token(mock_db_session, user_id, org_id)
        
        # Assert
        assert result == valid_token
    
    @pytest.mark.asyncio
    async def test_get_valid_salesforce_token_no_token(self, mock_db_session):
        """Test when no token exists for the user/org."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        mock_db_session.exec.return_value.first.return_value = None
        
        # Act
        result = await get_valid_salesforce_token(mock_db_session, user_id, org_id)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_valid_salesforce_token_no_access_token(self, mock_db_session):
        """Test when token record exists but has no access token."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        token_no_access = Mock(spec=OAuthToken)
        token_no_access.access_token = None
        
        mock_db_session.exec.return_value.first.return_value = token_no_access
        
        # Act
        result = await get_valid_salesforce_token(mock_db_session, user_id, org_id)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_valid_salesforce_token_expired_with_refresh(self, mock_db_session):
        """Test refreshing an expired token when refresh token is available."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        expired_token = Mock(spec=OAuthToken)
        expired_token.access_token = "expired_access_token"
        expired_token.valid_until = datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        expired_token.refresh_token = "valid_refresh_token"
        
        refreshed_token_data = Mock()
        refreshed_token_data.token_data = {'access_token': 'new_access_token'}
        
        mock_db_session.exec.return_value.first.return_value = expired_token
        
        with patch('app.crud.oauth.refresh_salesforce_token', new_callable=AsyncMock) as mock_refresh:
            with patch('app.crud.oauth.upsert_salesforce_token') as mock_upsert:
                mock_refresh.return_value = refreshed_token_data
                mock_upsert.return_value = refreshed_token_data
                
                # Act
                result = await get_valid_salesforce_token(mock_db_session, user_id, org_id)
                
                # Assert
                mock_refresh.assert_called_once_with("valid_refresh_token", user_id, org_id)
                mock_upsert.assert_called_once()
                assert result == refreshed_token_data
    
    @pytest.mark.asyncio
    async def test_get_valid_salesforce_token_expired_no_refresh(self, mock_db_session):
        """Test handling expired token with no refresh token."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        expired_token = Mock(spec=OAuthToken)
        expired_token.access_token = "expired_access_token"
        expired_token.valid_until = datetime.utcnow() - timedelta(hours=1)  # Expired
        expired_token.refresh_token = None  # No refresh token
        
        mock_db_session.exec.return_value.first.return_value = expired_token
        
        # Act
        result = await get_valid_salesforce_token(mock_db_session, user_id, org_id)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio 
    async def test_get_valid_salesforce_token_no_expiry_date(self, mock_db_session):
        """Test handling token with no expiry date."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        token_no_expiry = Mock(spec=OAuthToken)
        token_no_expiry.access_token = "access_token"
        token_no_expiry.valid_until = None  # No expiry date
        
        mock_db_session.exec.return_value.first.return_value = token_no_expiry
        
        # Act
        result = await get_valid_salesforce_token(mock_db_session, user_id, org_id)
        
        # Assert
        assert result == token_no_expiry  # Should return token if no expiry date


class TestDeleteSalesforceToken:
    """Test delete_salesforce_token function."""
    
    def test_delete_salesforce_token_success(self, mock_db_session):
        """Test successfully deleting a Salesforce token."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        provider = "salesforce"
        
        existing_token = Mock(spec=OAuthToken)
        mock_db_session.exec.return_value.first.return_value = existing_token
        
        # Act
        result = delete_salesforce_token(mock_db_session, user_id, org_id, provider)
        
        # Assert
        assert result is True
        mock_db_session.delete.assert_called_once_with(existing_token)
        mock_db_session.commit.assert_called_once()
    
    def test_delete_salesforce_token_not_found(self, mock_db_session):
        """Test deleting a token that doesn't exist."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        provider = "salesforce"
        
        mock_db_session.exec.return_value.first.return_value = None  # No token found
        
        # Act
        result = delete_salesforce_token(mock_db_session, user_id, org_id, provider)
        
        # Assert
        assert result is False
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()
    
    def test_delete_salesforce_token_different_provider(self, mock_db_session):
        """Test that provider filtering works correctly."""
        # Arrange
        user_id = "test_user_123"
        org_id = "test_org_456"
        provider = "google"  # Different provider
        
        mock_db_session.exec.return_value.first.return_value = None
        
        # Act
        result = delete_salesforce_token(mock_db_session, user_id, org_id, provider)
        
        # Assert
        assert result is False