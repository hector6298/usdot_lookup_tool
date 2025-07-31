"""
Unit tests for manual upload routes.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.routes.upload import upload_manual_usdots


class TestUploadManualUsdots:
    """Test upload_manual_usdots route."""
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_success(self, mock_request, mock_db_session):
        """Test successfully processing manual USDOT numbers."""
        # Arrange
        usdot_numbers = "123456, 789012, 345678"
        
        mock_ocr_results = [Mock(), Mock(), Mock()]
        for i, result in enumerate(mock_ocr_results):
            result.id = i + 1
            result.dot_reading = ["123456", "789012", "345678"][i]
        
        with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
            with patch('app.routes.upload.save_carrier_data_bulk') as mock_save_carrier:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    
                    mock_safer_data = Mock()
                    mock_safer_data.lookup_success_flag = True
                    mock_safer.return_value = mock_safer_data
                    
                    mock_save_carrier.return_value = [Mock()]
                    mock_save_ocr.return_value = mock_ocr_results
                    
                    # Act
                    result = await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
                    
                    # Assert
                    assert isinstance(result, JSONResponse)
                    assert result.status_code == 200
                    
                    # Verify SAFER lookup was called for each USDOT
                    assert mock_safer.call_count == 3
                    
                    # Verify bulk saves were called
                    mock_save_carrier.assert_called_once()
                    mock_save_ocr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_mixed_valid_invalid(self, mock_request, mock_db_session):
        """Test processing mix of valid and invalid USDOT numbers."""
        # Arrange
        usdot_numbers = "123456, invalid, 789012, 12345678901, 345678"  # Mix of valid and invalid
        
        mock_ocr_results = [Mock(), Mock(), Mock()]
        for i, result in enumerate(mock_ocr_results):
            result.id = i + 1
            result.dot_reading = ["123456", "789012", "345678"][i]
        
        with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
            with patch('app.routes.upload.save_carrier_data_bulk') as mock_save_carrier:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    
                    mock_safer_data = Mock()
                    mock_safer_data.lookup_success_flag = True
                    mock_safer.return_value = mock_safer_data
                    
                    mock_save_carrier.return_value = [Mock()]
                    mock_save_ocr.return_value = mock_ocr_results
                    
                    # Act
                    result = await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
                    
                    # Assert
                    assert isinstance(result, JSONResponse)
                    assert result.status_code == 200
                    
                    # Only valid USDOTs should be processed
                    assert mock_safer.call_count == 3  # 123456, 789012, 345678
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_empty_input(self, mock_request, mock_db_session):
        """Test handling empty input."""
        # Arrange
        usdot_numbers = ""
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "No USDOT numbers provided" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_whitespace_only(self, mock_request, mock_db_session):
        """Test handling whitespace-only input."""
        # Arrange
        usdot_numbers = "   \n\t   "
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "No USDOT numbers provided" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_all_invalid(self, mock_request, mock_db_session):
        """Test handling all invalid USDOT numbers."""
        # Arrange
        usdot_numbers = "invalid, abc123, 12345, 123456789"  # All invalid
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "No valid USDOT numbers found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_valid_range(self, mock_request, mock_db_session):
        """Test that valid USDOT numbers (6-8 digits) are accepted."""
        # Arrange
        usdot_numbers = "123456, 1234567, 12345678"  # 6, 7, and 8 digits
        
        mock_ocr_results = [Mock(), Mock(), Mock()]
        for i, result in enumerate(mock_ocr_results):
            result.id = i + 1
            result.dot_reading = ["123456", "1234567", "12345678"][i]
        
        with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
            mock_save_ocr.return_value = mock_ocr_results
            
            # Act
            result = await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
            
            # Assert
            assert isinstance(result, JSONResponse)
            assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_safer_lookup_failure(self, mock_request, mock_db_session):
        """Test handling SAFER lookup failures for manual input."""
        # Arrange
        usdot_numbers = "123456, 789012"
        
        mock_ocr_results = [Mock(), Mock()]
        for i, result in enumerate(mock_ocr_results):
            result.id = i + 1
            result.dot_reading = ["123456", "789012"][i]
        
        with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
            with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                
                mock_safer_data = Mock()
                mock_safer_data.lookup_success_flag = False  # Lookup failed
                mock_safer.return_value = mock_safer_data
                
                mock_save_ocr.return_value = mock_ocr_results
                
                # Act
                result = await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
                
                # Assert
                assert isinstance(result, JSONResponse)
                assert result.status_code == 200
                
                # SAFER lookup should be attempted but no carrier data saved
                assert mock_safer.call_count == 2
                mock_save_ocr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_manual_usdots_orphan_dot_reading(self, mock_request, mock_db_session):
        """Test handling orphan DOT reading (0000000) in manual input."""
        # Arrange
        usdot_numbers = "123456, 0000000, 789012"
        
        mock_ocr_results = [Mock(), Mock(), Mock()]
        for i, result in enumerate(mock_ocr_results):
            result.id = i + 1
            result.dot_reading = ["123456", "0000000", "789012"][i]
        
        with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
            with patch('app.routes.upload.save_carrier_data_bulk') as mock_save_carrier:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    
                    mock_safer_data = Mock()
                    mock_safer_data.lookup_success_flag = True
                    mock_safer.return_value = mock_safer_data
                    
                    mock_save_carrier.return_value = [Mock()]
                    mock_save_ocr.return_value = mock_ocr_results
                    
                    # Act
                    result = await upload_manual_usdots(usdot_numbers, mock_request, mock_db_session)
                    
                    # Assert
                    assert isinstance(result, JSONResponse)
                    assert result.status_code == 200
                    
                    # Should not perform SAFER lookup for orphan records (0000000)
                    assert mock_safer.call_count == 2  # Only for 123456 and 789012