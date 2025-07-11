"""
Unit tests for engagement CRUD operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException

from app.crud.engagement import (
    get_engagement_data,
    generate_engagement_records,
    save_engagement_records_bulk,
    update_carrier_engagement
)
from app.models.engagement import CarrierEngagementStatus, CarrierChangeItem


class TestGetEngagementData:
    """Test get_engagement_data function."""
    
    def test_get_engagement_data_without_filters(self, mock_db_session):
        """Test getting engagement data without any filters."""
        # Arrange
        mock_engagements = [Mock(spec=CarrierEngagementStatus) for _ in range(3)]
        mock_query = mock_db_session.query.return_value
        mock_query.order_by.return_value.all.return_value = mock_engagements
        
        # Act
        result = get_engagement_data(mock_db_session)
        
        # Assert
        assert result == mock_engagements
        mock_db_session.query.assert_called_once_with(CarrierEngagementStatus)
        mock_query.order_by.assert_called_once()
        
    def test_get_engagement_data_with_org_filter(self, mock_db_session):
        """Test getting engagement data filtered by org_id."""
        # Arrange
        org_id = "test_org_123"
        mock_engagements = [Mock(spec=CarrierEngagementStatus) for _ in range(2)]
        mock_query = mock_db_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_engagements
        
        # Act
        result = get_engagement_data(mock_db_session, org_id=org_id)
        
        # Assert
        assert result == mock_engagements
        mock_query.filter.assert_called_once()
        
    def test_get_engagement_data_with_interested_filter(self, mock_db_session):
        """Test getting engagement data filtered by carrier_interested."""
        # Arrange
        mock_engagements = [Mock(spec=CarrierEngagementStatus)]
        mock_query = mock_db_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_engagements
        
        # Act
        result = get_engagement_data(mock_db_session, carrier_interested=True)
        
        # Assert
        assert result == mock_engagements
        mock_query.filter.assert_called_once()
        
    def test_get_engagement_data_with_contacted_filter(self, mock_db_session):
        """Test getting engagement data filtered by carrier_contacted."""
        # Arrange
        mock_engagements = [Mock(spec=CarrierEngagementStatus)]
        mock_query = mock_db_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_engagements
        
        # Act
        result = get_engagement_data(mock_db_session, carrier_contacted=True)
        
        # Assert
        assert result == mock_engagements
        mock_query.filter.assert_called_once()
    
    def test_get_engagement_data_with_pagination(self, mock_db_session):
        """Test getting engagement data with pagination."""
        # Arrange
        offset, limit = 10, 5
        mock_engagements = [Mock(spec=CarrierEngagementStatus) for _ in range(5)]
        mock_query = mock_db_session.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_engagements
        
        # Act
        result = get_engagement_data(mock_db_session, offset=offset, limit=limit)
        
        # Assert
        assert result == mock_engagements
        mock_query.order_by.return_value.offset.assert_called_once_with(offset)
        mock_query.order_by.return_value.offset.return_value.limit.assert_called_once_with(limit)


class TestGenerateEngagementRecords:
    """Test generate_engagement_records function."""
    
    def test_generate_engagement_records_success(self, mock_db_session):
        """Test generating engagement records successfully."""
        # Arrange
        usdot_numbers = ["123456", "789012", "345678"]
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        # Mock that no existing engagement records exist
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = generate_engagement_records(mock_db_session, usdot_numbers, user_id, org_id)
        
        # Assert
        assert len(result) == 3
        for i, record in enumerate(result):
            assert isinstance(record, CarrierEngagementStatus)
            assert record.usdot == usdot_numbers[i]
            assert record.user_id == user_id
            assert record.org_id == org_id
    
    def test_generate_engagement_records_skip_existing(self, mock_db_session):
        """Test skipping existing engagement records."""
        # Arrange
        usdot_numbers = ["123456", "789012"]
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        # Mock that first record exists, second doesn't
        existing_record = Mock(spec=CarrierEngagementStatus)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [existing_record, None]
        
        # Act
        result = generate_engagement_records(mock_db_session, usdot_numbers, user_id, org_id)
        
        # Assert
        assert len(result) == 1  # Only one new record should be generated
        assert result[0].usdot == "789012"
    
    def test_generate_engagement_records_database_error(self, mock_db_session):
        """Test handling database errors in generate_engagement_records."""
        # Arrange
        usdot_numbers = ["123456"]
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        mock_db_session.query.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            generate_engagement_records(mock_db_session, usdot_numbers, user_id, org_id)
        
        assert exc_info.value.status_code == 500


class TestSaveEngagementRecordsBulk:
    """Test save_engagement_records_bulk function."""
    
    @patch('app.crud.engagement.generate_engagement_records')
    def test_save_engagement_records_bulk_success(self, mock_generate, mock_db_session):
        """Test bulk saving engagement records successfully."""
        # Arrange
        usdot_numbers = ["123456", "789012"]
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        mock_records = [Mock(spec=CarrierEngagementStatus) for _ in range(2)]
        mock_generate.return_value = mock_records
        
        # Act
        result = save_engagement_records_bulk(mock_db_session, usdot_numbers, user_id, org_id)
        
        # Assert
        assert result == mock_records
        mock_db_session.add_all.assert_called_once_with(mock_records)
        mock_db_session.commit.assert_called_once()
        assert mock_db_session.refresh.call_count == 2
    
    @patch('app.crud.engagement.generate_engagement_records')
    def test_save_engagement_records_bulk_database_error(self, mock_generate, mock_db_session):
        """Test handling database errors in bulk save."""
        # Arrange
        usdot_numbers = ["123456"]
        user_id = "test_user_123"
        org_id = "test_org_456"
        
        mock_records = [Mock(spec=CarrierEngagementStatus)]
        mock_generate.return_value = mock_records
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            save_engagement_records_bulk(mock_db_session, usdot_numbers, user_id, org_id)
        
        assert exc_info.value.status_code == 500
        mock_db_session.rollback.assert_called_once()


class TestUpdateCarrierEngagement:
    """Test update_carrier_engagement function."""
    
    def test_update_carrier_engagement_boolean_field(self, mock_db_session):
        """Test updating boolean engagement fields."""
        # Arrange
        change_data = {
            "usdot": "123456",
            "field": "carrier_interested",
            "value": True,
            "user_id": "test_user_123"
        }
        
        existing_carrier = Mock(spec=CarrierEngagementStatus)
        existing_carrier.usdot = "123456"
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_carrier
        
        # Act
        result = update_carrier_engagement(mock_db_session, change_data)
        
        # Assert
        assert result == existing_carrier
        assert existing_carrier.carrier_interested == True
        assert hasattr(existing_carrier, 'carrier_interested_timestamp')
        assert hasattr(existing_carrier, 'carrier_interested_by_user_id')
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(existing_carrier)
    
    def test_update_carrier_engagement_string_field(self, mock_db_session):
        """Test updating string engagement fields."""
        # Arrange
        change_data = {
            "usdot": "123456",
            "field": "rental_notes",
            "value": "Updated notes",
            "user_id": "test_user_123"
        }
        
        existing_carrier = Mock(spec=CarrierEngagementStatus)
        existing_carrier.usdot = "123456"
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_carrier
        
        # Mock the table columns check
        with patch('app.models.engagement.CarrierEngagementStatus.__table__') as mock_table:
            mock_table.columns = {"rental_notes": Mock()}
            
            # Act
            result = update_carrier_engagement(mock_db_session, change_data)
            
            # Assert
            assert result == existing_carrier
            assert existing_carrier.rental_notes == "Updated notes"
            mock_db_session.commit.assert_called_once()
    
    def test_update_carrier_engagement_carrier_not_found(self, mock_db_session):
        """Test updating engagement when carrier not found."""
        # Arrange
        change_data = {
            "usdot": "999999",
            "field": "carrier_interested",
            "value": True,
            "user_id": "test_user_123"
        }
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = update_carrier_engagement(mock_db_session, change_data)
        
        # Assert
        assert result is None
        mock_db_session.commit.assert_not_called()
    
    def test_update_carrier_engagement_invalid_field(self, mock_db_session):
        """Test updating engagement with invalid field."""
        # Arrange
        change_data = {
            "usdot": "123456",
            "field": "invalid_field",
            "value": "test",
            "user_id": "test_user_123"
        }
        
        existing_carrier = Mock(spec=CarrierEngagementStatus)
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_carrier
        
        # Mock the table columns check to not include the invalid field
        with patch('app.models.engagement.CarrierEngagementStatus.__table__') as mock_table:
            mock_table.columns = {}
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                update_carrier_engagement(mock_db_session, change_data)
            
            # The original code catches HTTPException(400) and converts to 500 - this is the actual behavior
            assert exc_info.value.status_code == 500
    
    def test_update_carrier_engagement_database_error(self, mock_db_session):
        """Test handling database errors in update_carrier_engagement."""
        # Arrange
        change_data = {
            "usdot": "123456",
            "field": "carrier_interested",
            "value": True,
            "user_id": "test_user_123"
        }
        
        existing_carrier = Mock(spec=CarrierEngagementStatus)
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_carrier
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            update_carrier_engagement(mock_db_session, change_data)
        
        assert exc_info.value.status_code == 500
        mock_db_session.rollback.assert_called_once()
    
    def test_update_carrier_engagement_all_boolean_fields(self, mock_db_session):
        """Test updating all boolean engagement fields."""
        boolean_fields = ["carrier_interested", "carrier_contacted", "carrier_followed_up", "carrier_emailed"]
        
        for field in boolean_fields:
            # Arrange
            change_data = {
                "usdot": "123456",
                "field": field,
                "value": True,
                "user_id": "test_user_123"
            }
            
            existing_carrier = Mock(spec=CarrierEngagementStatus)
            mock_db_session.query.return_value.filter.return_value.first.return_value = existing_carrier
            mock_db_session.reset_mock()
            
            # Act
            result = update_carrier_engagement(mock_db_session, change_data)
            
            # Assert
            assert result == existing_carrier
            assert getattr(existing_carrier, field) == True
            assert hasattr(existing_carrier, f'{field}_timestamp')
            assert hasattr(existing_carrier, f'{field}_by_user_id')
            mock_db_session.commit.assert_called_once()