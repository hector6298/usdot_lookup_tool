"""
Unit tests for carrier_data CRUD operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from app.crud.carrier_data import (
    get_carrier_data,
    get_carrier_data_by_dot,
    save_carrier_data,
    generate_carrier_records,
    save_carrier_data_bulk
)
from app.models.carrier_data import CarrierData, CarrierDataCreate


class TestGetCarrierData:
    """Test get_carrier_data function."""
    
    def test_get_carrier_data_without_org_id(self, mock_db_session):
        """Test getting carrier data without org filtering."""
        # Arrange
        mock_carriers = [Mock(spec=CarrierData) for _ in range(3)]
        mock_db_session.exec.return_value.all.return_value = mock_carriers
        
        # Act
        result = get_carrier_data(mock_db_session)
        
        # Assert
        assert result == mock_carriers
        mock_db_session.exec.assert_called_once()
        
    def test_get_carrier_data_with_org_id(self, mock_db_session):
        """Test getting carrier data with org filtering."""
        # Arrange
        org_id = "test_org_123"
        from app.models.sobject_sync_status import CRMSyncStatus
        mock_sync_records = [Mock(usdot="123456"), Mock(usdot="789012")]
        mock_carriers = [Mock(spec=CarrierData) for _ in range(2)]
        
        # Mock the CRM sync status query and carrier data query
        mock_db_session.exec.side_effect = [
            Mock(all=Mock(return_value=mock_sync_records)),  # CRM sync query
            Mock(all=Mock(return_value=mock_carriers))       # Carrier data query
        ]
        
        # Act  
        result = get_carrier_data(mock_db_session, org_id=org_id)
        
        # Assert
        assert result == mock_carriers
        assert mock_db_session.exec.call_count == 2
            
    def test_get_carrier_data_with_pagination(self, mock_db_session):
        """Test getting carrier data with pagination."""
        # Arrange
        offset, limit = 10, 5
        mock_carriers = [Mock(spec=CarrierData) for _ in range(5)]
        
        mock_db_session.exec.return_value.all.return_value = mock_carriers
        
        # Act
        result = get_carrier_data(mock_db_session, offset=offset, limit=limit)
        
        # Assert
        assert result == mock_carriers
        mock_db_session.exec.assert_called_once()


class TestGetCarrierDataByDot:
    """Test get_carrier_data_by_dot function."""
    
    def test_get_carrier_data_by_dot_found(self, mock_db_session, sample_carrier_db_record):
        """Test getting carrier data by DOT number when carrier exists."""
        # Arrange
        dot_number = "123456"
        mock_db_session.exec.return_value.first.return_value = sample_carrier_db_record
        
        # Act
        result = get_carrier_data_by_dot(mock_db_session, dot_number)
        
        # Assert
        assert result == sample_carrier_db_record
        mock_db_session.exec.assert_called_once()
        
    def test_get_carrier_data_by_dot_not_found(self, mock_db_session):
        """Test getting carrier data by DOT number when carrier doesn't exist."""
        # Arrange
        dot_number = "999999"
        mock_db_session.exec.return_value.first.return_value = None
        
        # Act
        result = get_carrier_data_by_dot(mock_db_session, dot_number)
        
        # Assert
        assert result is None
        mock_db_session.exec.assert_called_once()


class TestSaveCarrierData:
    """Test save_carrier_data function."""
    
    def test_save_carrier_data_new_record(self, mock_db_session, sample_carrier_data):
        """Test saving new carrier data."""
        # Arrange
        mock_db_session.exec.return_value.first.return_value = None
        
        with patch('app.models.carrier_data.CarrierData.model_validate') as mock_validate:
            mock_carrier_record = Mock(spec=CarrierData)
            mock_carrier_record.legal_name = "Test Carrier LLC"
            mock_validate.return_value = mock_carrier_record
            
            # Act
            result = save_carrier_data(mock_db_session, sample_carrier_data)
            
            # Assert
            assert result == mock_carrier_record
            mock_db_session.add.assert_called_once_with(mock_carrier_record)
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once_with(mock_carrier_record)
    
    def test_save_carrier_data_existing_record(self, mock_db_session, sample_carrier_data):
        """Test updating existing carrier data."""
        # Arrange
        existing_carrier = Mock(spec=CarrierData)
        existing_carrier.legal_name = "Old Name"
        mock_db_session.exec.return_value.first.return_value = existing_carrier
        
        with patch('app.models.carrier_data.CarrierData.model_validate') as mock_validate:
            mock_carrier_record = Mock(spec=CarrierData)
            mock_carrier_record.model_dump.return_value = {"legal_name": "New Name", "usdot": "123456"}
            mock_validate.return_value = mock_carrier_record
            
            # Act
            result = save_carrier_data(mock_db_session, sample_carrier_data)
            
            # Assert
            assert result == existing_carrier
            mock_db_session.add.assert_not_called()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once_with(existing_carrier)
    
    def test_save_carrier_data_database_error(self, mock_db_session, sample_carrier_data):
        """Test handling database errors when saving carrier data."""
        # Arrange
        mock_db_session.exec.return_value.first.return_value = None
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with patch('app.models.carrier_data.CarrierData.model_validate') as mock_validate:
            mock_validate.return_value = Mock(spec=CarrierData)
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                save_carrier_data(mock_db_session, sample_carrier_data)
            
            assert exc_info.value.status_code == 500
            mock_db_session.rollback.assert_called_once()


class TestGenerateCarrierRecords:
    """Test generate_carrier_records function."""
    
    def test_generate_carrier_records_success(self, mock_db_session):
        """Test generating carrier records successfully."""
        # Arrange
        carrier_data_list = [
            CarrierDataCreate(usdot="123456", legal_name="Carrier 1", lookup_success_flag=True),
            CarrierDataCreate(usdot="789012", legal_name="Carrier 2", lookup_success_flag=True)
        ]
        
        mock_db_session.exec.return_value.first.return_value = None
        
        with patch('app.models.carrier_data.CarrierData.model_validate') as mock_validate:
            mock_records = [Mock(spec=CarrierData) for _ in range(2)]
            mock_validate.side_effect = mock_records
            
            # Act
            result = generate_carrier_records(mock_db_session, carrier_data_list)
            
            # Assert
            assert len(result) == 2
            assert all(isinstance(record, Mock) for record in result)
    
    def test_generate_carrier_records_validation_error(self, mock_db_session):
        """Test handling validation errors in generate_carrier_records."""
        # Arrange
        carrier_data_list = [
            CarrierDataCreate(usdot="invalid", legal_name="Invalid Carrier", lookup_success_flag=True)
        ]
        
        with patch('app.models.carrier_data.CarrierData.model_validate') as mock_validate:
            mock_validate.side_effect = Exception("Validation error")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                generate_carrier_records(mock_db_session, carrier_data_list)
            
            assert exc_info.value.status_code == 500


class TestSaveCarrierDataBulk:
    """Test save_carrier_data_bulk function."""
    
    @patch('app.crud.carrier_data.generate_crm_sync_records')
    @patch('app.crud.carrier_data.generate_carrier_records')
    def test_save_carrier_data_bulk_success(self, mock_gen_carriers, mock_gen_sync, mock_db_session):
        """Test bulk saving carrier data successfully."""
        # Arrange
        carrier_data_list = [
            CarrierDataCreate(usdot="123456", legal_name="Carrier 1", lookup_success_flag=True),
            CarrierDataCreate(usdot="789012", legal_name="Carrier 2", lookup_success_flag=True)
        ]
        user_id = "test_user"
        org_id = "test_org"
        
        mock_carrier_records = [Mock(spec=CarrierData) for _ in range(2)]
        mock_sync_records = [Mock() for _ in range(2)]
        
        mock_gen_carriers.return_value = mock_carrier_records
        mock_gen_sync.return_value = mock_sync_records
        
        # Act
        result = save_carrier_data_bulk(mock_db_session, carrier_data_list, user_id, org_id)
        
        # Assert
        assert result == mock_carrier_records
        mock_db_session.add_all.assert_any_call(mock_carrier_records)
        mock_db_session.add_all.assert_any_call(mock_sync_records)
        mock_db_session.commit.assert_called_once()
        
    @patch('app.crud.carrier_data.generate_crm_sync_records')
    @patch('app.crud.carrier_data.generate_carrier_records')
    def test_save_carrier_data_bulk_no_records(self, mock_gen_carriers, mock_gen_sync, mock_db_session):
        """Test bulk saving when no valid records to save."""
        # Arrange
        carrier_data_list = []
        user_id = "test_user"
        org_id = "test_org"
        
        mock_gen_carriers.return_value = []
        mock_gen_sync.return_value = []
        
        # Act
        result = save_carrier_data_bulk(mock_db_session, carrier_data_list, user_id, org_id)
        
        # Assert
        assert result == []
        mock_db_session.add_all.assert_not_called()
        mock_db_session.commit.assert_not_called()
    
    @patch('app.crud.carrier_data.generate_crm_sync_records')
    @patch('app.crud.carrier_data.generate_carrier_records')
    def test_save_carrier_data_bulk_database_error(self, mock_gen_carriers, mock_gen_sync, mock_db_session):
        """Test handling database errors in bulk save."""
        # Arrange
        carrier_data_list = [
            CarrierDataCreate(usdot="123456", legal_name="Carrier 1", lookup_success_flag=True)
        ]
        user_id = "test_user"
        org_id = "test_org"
        
        mock_carrier_records = [Mock(spec=CarrierData)]
        mock_sync_records = [Mock()]
        
        mock_gen_carriers.return_value = mock_carrier_records
        mock_gen_sync.return_value = mock_sync_records
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            save_carrier_data_bulk(mock_db_session, carrier_data_list, user_id, org_id)
        
        assert exc_info.value.status_code == 500
        mock_db_session.rollback.assert_called_once()