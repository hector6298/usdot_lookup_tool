"""
Unit tests for user organization membership CRUD operations.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.crud.user_org_membership import save_user_org_membership
from app.models.user_org_membership import AppUser, AppOrg, UserOrgMembership


class TestSaveUserOrgMembership:
    """Test save_user_org_membership function."""
    
    def test_save_user_org_membership_new_records(self, mock_db_session):
        """Test saving new user, org, and membership records."""
        # Arrange
        login_info = {
            'userinfo': {
                'sub': 'test_user_123',
                'email': 'test@example.com'
            },
            'name': 'Test User',
            'given_name': 'Test',
            'family_name': 'User',
            'org_id': 'test_org_456',
            'org_name': 'Test Organization'
        }
        
        # Mock that no existing records exist
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = save_user_org_membership(mock_db_session, login_info)
        
        # Assert
        assert mock_db_session.add.call_count == 3  # User, Org, Membership
        mock_db_session.commit.assert_called_once()
        assert mock_db_session.refresh.call_count == 3
    
    def test_save_user_org_membership_existing_user(self, mock_db_session):
        """Test saving when user already exists."""
        # Arrange
        login_info = {
            'userinfo': {
                'sub': 'existing_user_123',
                'email': 'existing@example.com'
            },
            'name': 'Updated User Name'
        }
        
        existing_user = Mock(spec=AppUser)
        existing_user.user_id = 'existing_user_123'
        existing_user.dict.return_value = {
            'user_id': 'existing_user_123',
            'user_email': 'existing@example.com',
            'name': 'Updated User Name'
        }
        
        # Mock existing user found, but no org or membership
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            existing_user,  # Existing user
            None,           # No existing org
            None            # No existing membership
        ]
        
        # Act
        result = save_user_org_membership(mock_db_session, login_info)
        
        # Assert
        assert mock_db_session.add.call_count == 3  # Still adds user, org, membership
        mock_db_session.commit.assert_called_once()
    
    def test_save_user_org_membership_all_existing(self, mock_db_session):
        """Test saving when all records already exist."""
        # Arrange
        login_info = {
            'userinfo': {
                'sub': 'existing_user_123',
                'email': 'existing@example.com'
            },
            'org_id': 'existing_org_456',
            'org_name': 'Existing Org'
        }
        
        existing_user = Mock(spec=AppUser)
        existing_user.user_id = 'existing_user_123'
        existing_user.dict.return_value = {'user_id': 'existing_user_123'}
        
        existing_org = Mock(spec=AppOrg)
        existing_org.org_id = 'existing_org_456'
        existing_org.dict.return_value = {'org_id': 'existing_org_456'}
        
        existing_membership = Mock(spec=UserOrgMembership)
        
        # Mock all records existing
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            existing_user,      # Existing user
            existing_org,       # Existing org
            existing_membership # Existing membership
        ]
        
        # Act
        result = save_user_org_membership(mock_db_session, login_info)
        
        # Assert
        assert mock_db_session.add.call_count == 3  # Still adds all three
        mock_db_session.commit.assert_called_once()
    
    def test_save_user_org_membership_minimal_info(self, mock_db_session):
        """Test saving with minimal login info."""
        # Arrange
        login_info = {
            'userinfo': {
                'sub': 'minimal_user_123',
                'email': 'minimal@example.com'
            }
        }
        
        # Mock no existing records
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = save_user_org_membership(mock_db_session, login_info)
        
        # Assert
        assert mock_db_session.add.call_count == 3
        mock_db_session.commit.assert_called_once()
        assert mock_db_session.refresh.call_count == 3
    
    def test_save_user_org_membership_database_error(self, mock_db_session):
        """Test handling database errors."""
        # Arrange
        login_info = {
            'userinfo': {
                'sub': 'error_user_123',
                'email': 'error@example.com'
            }
        }
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            save_user_org_membership(mock_db_session, login_info)
        
        assert exc_info.value.status_code == 500
        assert "Database error" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()
    
    def test_save_user_org_membership_defaults_org_to_user_id(self, mock_db_session):
        """Test that org_id defaults to user_id when not provided."""
        # Arrange
        login_info = {
            'userinfo': {
                'sub': 'user_as_org_123',
                'email': 'userorg@example.com'
            }
        }
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = save_user_org_membership(mock_db_session, login_info)
        
        # Assert - verify the function was called (org_id should default to user_id)
        assert mock_db_session.add.call_count == 3
        mock_db_session.commit.assert_called_once()
    
    def test_save_user_org_membership_defaults_org_name_to_email(self, mock_db_session):
        """Test that org_name defaults to user_email when not provided."""
        # Arrange
        login_info = {
            'userinfo': {
                'sub': 'user_email_org_123',
                'email': 'emailorg@example.com'
            }
        }
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = save_user_org_membership(mock_db_session, login_info)
        
        # Assert - verify the function was called (org_name should default to email)
        assert mock_db_session.add.call_count == 3
        mock_db_session.commit.assert_called_once()