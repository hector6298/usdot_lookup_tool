"""
Unit tests for data routes.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.routes.data import (
    fetch_carriers,
    fetch_carrier,
    fetch_lookup_history,
    update_carrier_interests,
    export_carriers,
    export_lookup_history
)


class TestFetchCarriers:
    """Test fetch_carriers route."""
    
    @pytest.mark.asyncio
    async def test_fetch_carriers_success(self, mock_request, mock_db_session):
        """Test successfully fetching carriers."""
        # Arrange
        mock_carriers = [Mock() for _ in range(3)]
        for i, carrier in enumerate(mock_carriers):
            carrier.usdot = f"12345{i}"
            carrier.carrier_data.legal_name = f"Carrier {i}"
            carrier.carrier_data.phone = f"555-000-000{i}"
            carrier.carrier_data.mailing_address = f"Address {i}"
            carrier.created_at.strftime.return_value = "2023-01-01 12:00:00"
            carrier.carrier_interested = False
            carrier.carrier_contacted = False
            carrier.carrier_followed_up = False
            carrier.carrier_follow_up_by_date = None
        
        with patch('app.routes.data.get_engagement_data') as mock_get_engagement:
            mock_get_engagement.return_value = mock_carriers
            
            # Act
            result = await fetch_carriers(
                mock_request,
                offset=0,
                limit=10,
                carrier_interested=None,
                client_contacted=None,
                db=mock_db_session
            )
            
            # Assert
            assert len(result) == 3
            mock_get_engagement.assert_called_once_with(
                mock_db_session,
                org_id='test_org_456',
                offset=0,
                carrier_contacted=None,
                carrier_interested=None,
                limit=10
            )
    
    @pytest.mark.asyncio
    async def test_fetch_carriers_with_filters(self, mock_request, mock_db_session):
        """Test fetching carriers with filters applied."""
        # Arrange
        mock_carriers = [Mock()]
        mock_carriers[0].usdot = "123456"
        mock_carriers[0].carrier_data.legal_name = "Interested Carrier"
        mock_carriers[0].carrier_data.phone = "555-000-0001"
        mock_carriers[0].carrier_data.mailing_address = "Address 1"
        mock_carriers[0].created_at.strftime.return_value = "2023-01-01 12:00:00"
        mock_carriers[0].carrier_interested = True
        mock_carriers[0].carrier_contacted = True
        mock_carriers[0].carrier_followed_up = False
        mock_carriers[0].carrier_follow_up_by_date = None
        
        with patch('app.routes.data.get_engagement_data') as mock_get_engagement:
            mock_get_engagement.return_value = mock_carriers
            
            # Act
            result = await fetch_carriers(
                mock_request,
                offset=5,
                limit=5,
                carrier_interested=True,
                client_contacted=True,
                db=mock_db_session
            )
            
            # Assert
            assert len(result) == 1
            assert result[0].carrier_interested is True
            assert result[0].carrier_contacted is True
            mock_get_engagement.assert_called_once_with(
                mock_db_session,
                org_id='test_org_456',
                offset=5,
                carrier_contacted=True,
                carrier_interested=True,
                limit=5
            )
    
    @pytest.mark.asyncio
    async def test_fetch_carriers_empty_result(self, mock_request, mock_db_session):
        """Test fetching carriers when no results found."""
        # Arrange
        with patch('app.routes.data.get_engagement_data') as mock_get_engagement:
            mock_get_engagement.return_value = []
            
            # Act
            result = await fetch_carriers(mock_request, db=mock_db_session)
            
            # Assert
            assert result == []


class TestFetchCarrier:
    """Test fetch_carrier route."""
    
    def test_fetch_carrier_found(self, mock_request, mock_db_session, sample_carrier_db_record):
        """Test fetching a specific carrier by DOT number."""
        # Arrange
        dot_number = "123456"
        
        with patch('app.routes.data.get_carrier_data_by_dot') as mock_get_carrier:
            mock_get_carrier.return_value = sample_carrier_db_record
            
            # Act
            result = fetch_carrier(mock_request, dot_number, mock_db_session)
            
            # Assert
            assert result == sample_carrier_db_record
            mock_get_carrier.assert_called_once_with(mock_db_session, dot_number)
    
    def test_fetch_carrier_not_found(self, mock_request, mock_db_session):
        """Test fetching a carrier that doesn't exist."""
        # Arrange
        dot_number = "999999"
        
        with patch('app.routes.data.get_carrier_data_by_dot') as mock_get_carrier:
            mock_get_carrier.return_value = None
            
            # Act
            result = fetch_carrier(mock_request, dot_number, mock_db_session)
            
            # Assert
            assert isinstance(result, JSONResponse)
            assert result.status_code == 404


class TestFetchLookupHistory:
    """Test fetch_lookup_history route."""
    
    @pytest.mark.asyncio
    async def test_fetch_lookup_history_success(self, mock_request, mock_db_session):
        """Test successfully fetching lookup history."""
        # Arrange
        mock_results = [Mock() for _ in range(2)]
        for i, result in enumerate(mock_results):
            result.dot_reading = f"12345{i}"
            result.carrier_data.legal_name = f"Carrier {i}"
            result.carrier_data.phone = f"555-000-000{i}"
            result.carrier_data.mailing_address = f"Address {i}"
            result.timestamp.strftime.return_value = "2023-01-01 12:00:00"
            result.filename = f"image{i}.jpg"
            result.app_user.user_email = f"user{i}@example.com"
            result.app_org.org_name = f"Org {i}"
        
        with patch('app.routes.data.get_ocr_results') as mock_get_ocr:
            mock_get_ocr.return_value = mock_results
            
            # Act
            result = await fetch_lookup_history(
                mock_request,
                offset=0,
                limit=10,
                valid_dot_only=False,
                db=mock_db_session
            )
            
            # Assert
            assert len(result) == 2
            mock_get_ocr.assert_called_once_with(
                mock_db_session,
                org_id='test_org_456',
                offset=0,
                limit=10,
                valid_dot_only=False,
                eager_relations=True
            )
    
    @pytest.mark.asyncio
    async def test_fetch_lookup_history_with_no_carrier_data(self, mock_request, mock_db_session):
        """Test fetching lookup history when carrier data is None."""
        # Arrange
        mock_result = Mock()
        mock_result.dot_reading = "123456"
        mock_result.carrier_data = None  # No carrier data
        mock_result.timestamp.strftime.return_value = "2023-01-01 12:00:00"
        mock_result.filename = "image.jpg"
        mock_result.app_user.user_email = "user@example.com"
        mock_result.app_org.org_name = "Test Org"
        
        with patch('app.routes.data.get_ocr_results') as mock_get_ocr:
            mock_get_ocr.return_value = [mock_result]
            
            # Act
            result = await fetch_lookup_history(mock_request, db=mock_db_session)
            
            # Assert
            assert len(result) == 1
            assert result[0].legal_name == ""
            assert result[0].phone == ""
            assert result[0].mailing_address == ""


class TestUpdateCarrierInterests:
    """Test update_carrier_interests route."""
    
    @pytest.mark.asyncio
    async def test_update_carrier_interests_success(self, mock_request, mock_db_session):
        """Test successfully updating carrier interests."""
        # Arrange
        mock_request.json = AsyncMock(return_value={
            "changes": [
                {
                    "usdot": "123456",
                    "field": "carrier_interested",
                    "value": True
                },
                {
                    "usdot": "789012",
                    "field": "carrier_contacted",
                    "value": True
                }
            ]
        })
        
        with patch('app.routes.data.update_carrier_engagement') as mock_update:
            mock_update.return_value = Mock()  # Successful update
            
            # Act
            result = await update_carrier_interests(mock_request, mock_db_session)
            
            # Assert
            assert isinstance(result, JSONResponse)
            assert result.status_code == 200
            assert mock_update.call_count == 2
    
    @pytest.mark.asyncio
    async def test_update_carrier_interests_missing_data(self, mock_request, mock_db_session):
        """Test updating with missing required data."""
        # Arrange
        mock_request.json = AsyncMock(return_value={
            "changes": [
                {
                    "usdot": "123456",
                    "field": "carrier_interested"
                    # Missing 'value' field
                }
            ]
        })
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_carrier_interests(mock_request, mock_db_session)
        
        # The actual behavior is that this gets caught and converted to 500
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_update_carrier_interests_database_error(self, mock_request, mock_db_session):
        """Test handling database errors during update."""
        # Arrange
        mock_request.json = AsyncMock(return_value={
            "changes": [
                {
                    "usdot": "123456",
                    "field": "carrier_interested",
                    "value": True
                }
            ]
        })
        
        with patch('app.routes.data.update_carrier_engagement') as mock_update:
            mock_update.side_effect = Exception("Database error")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await update_carrier_interests(mock_request, mock_db_session)
            
            assert exc_info.value.status_code == 500


class TestExportCarriers:
    """Test export_carriers route."""
    
    @pytest.mark.asyncio
    async def test_export_carriers_success(self, mock_request, mock_db_session):
        """Test successfully exporting carrier data."""
        # Arrange
        mock_carriers = [Mock() for _ in range(2)]
        for i, carrier in enumerate(mock_carriers):
            carrier.usdot = f"12345{i}"
            carrier.carrier_data.legal_name = f"Carrier {i}"
            carrier.carrier_data.phone = f"555-000-000{i}"
            carrier.carrier_data.mailing_address = f"Address {i}"
            carrier.created_at.strftime.return_value = "2023-01-01 12:00:00"
            carrier.carrier_contacted = False
            carrier.carrier_followed_up = False
            carrier.carrier_follow_up_by_date = None
            carrier.carrier_interested = False
        
        with patch('app.routes.data.get_engagement_data') as mock_get_engagement:
            mock_get_engagement.return_value = mock_carriers
            
            # Act
            result = await export_carriers(mock_request, mock_db_session)
            
            # Assert
            assert result.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "carrier_data.xlsx" in result.headers["Content-Disposition"]
            mock_get_engagement.assert_called_once_with(mock_db_session, org_id='test_org_456')


class TestExportLookupHistory:
    """Test export_lookup_history route."""
    
    @pytest.mark.asyncio
    async def test_export_lookup_history_success(self, mock_request, mock_db_session):
        """Test successfully exporting lookup history."""
        # Arrange
        mock_results = [Mock() for _ in range(2)]
        for i, result in enumerate(mock_results):
            result.dot_reading = f"12345{i}"
            result.carrier_data.legal_name = f"Carrier {i}"
            result.carrier_data.phone = f"555-000-000{i}"
            result.carrier_data.mailing_address = f"Address {i}"
            result.timestamp.strftime.return_value = "2023-01-01 12:00:00"
            result.filename = f"image{i}.jpg"
            result.app_user.user_email = f"user{i}@example.com"
        
        with patch('app.routes.data.get_ocr_results') as mock_get_ocr:
            mock_get_ocr.return_value = mock_results
            
            # Act
            result = await export_lookup_history(mock_request, mock_db_session)
            
            # Assert
            assert result.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "lookup_history.xlsx" in result.headers["Content-Disposition"]
            mock_get_ocr.assert_called_once_with(
                mock_db_session,
                org_id='test_org_456',
                valid_dot_only=False,
                eager_relations=True
            )
    
    @pytest.mark.asyncio
    async def test_export_lookup_history_no_carrier_data(self, mock_request, mock_db_session):
        """Test exporting lookup history when some entries have no carrier data."""
        # Arrange
        mock_result = Mock()
        mock_result.dot_reading = "123456"
        mock_result.carrier_data = None  # No carrier data
        mock_result.timestamp.strftime.return_value = "2023-01-01 12:00:00"
        mock_result.filename = "image.jpg"
        mock_result.app_user.user_email = "user@example.com"
        
        with patch('app.routes.data.get_ocr_results') as mock_get_ocr:
            mock_get_ocr.return_value = [mock_result]
            
            # Act
            result = await export_lookup_history(mock_request, mock_db_session)
            
            # Assert
            assert result.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "lookup_history.xlsx" in result.headers["Content-Disposition"]