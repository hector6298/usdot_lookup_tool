"""
Unit tests for upload routes.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.routes.upload import upload_file


class TestUploadFile:
    """Test upload_file route."""
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_request, mock_db_session):
        """Test successfully uploading and processing files."""
        # Arrange
        mock_files = [Mock(spec=UploadFile), Mock(spec=UploadFile)]
        mock_files[0].filename = "test1.jpg"
        mock_files[1].filename = "test2.png"
        
        mock_ocr_records = [Mock(), Mock()]
        for i, record in enumerate(mock_ocr_records):
            record.dot_reading = f"12345{i}"
        
        mock_ocr_results = [Mock(), Mock()]
        for i, result in enumerate(mock_ocr_results):
            result.id = i + 1
            result.dot_reading = f"12345{i}"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
                    with patch('app.routes.upload.save_carrier_data_bulk') as mock_save_carrier:
                        with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                            
                            mock_ocr.return_value = "USDOT 123456 TEST CARRIER"
                            mock_generate.side_effect = mock_ocr_records
                            
                            mock_safer_data = Mock()
                            mock_safer_data.lookup_success_flag = True
                            mock_safer.return_value = mock_safer_data
                            
                            mock_save_carrier.return_value = [Mock()]
                            mock_save_ocr.return_value = mock_ocr_results
                            
                            # Act
                            result = await upload_file(mock_files, mock_request, mock_db_session)
                            
                            # Assert
                            assert isinstance(result, JSONResponse)
                            assert result.status_code == 200
                            
                            # Verify OCR was called for each file
                            assert mock_ocr.call_count == 2
                            assert mock_generate.call_count == 2
                            
                            # Verify safer lookup was called for valid DOT readings
                            assert mock_safer.call_count == 2
                            
                            # Verify bulk saves were called
                            mock_save_carrier.assert_called_once()
                            mock_save_ocr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_file_invalid_file_types(self, mock_request, mock_db_session):
        """Test uploading files with invalid file types."""
        # Arrange
        mock_files = [Mock(spec=UploadFile), Mock(spec=UploadFile)]
        mock_files[0].filename = "document.pdf"  # Invalid type
        mock_files[1].filename = "test.jpg"      # Valid type
        
        mock_ocr_record = Mock()
        mock_ocr_record.dot_reading = "123456"
        
        mock_ocr_result = Mock()
        mock_ocr_result.id = 1
        mock_ocr_result.dot_reading = "123456"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    
                    mock_ocr.return_value = "USDOT 123456 TEST CARRIER"
                    mock_generate.return_value = mock_ocr_record
                    mock_save_ocr.return_value = [mock_ocr_result]
                    
                    # Act
                    result = await upload_file(mock_files, mock_request, mock_db_session)
                    
                    # Assert
                    assert isinstance(result, JSONResponse)
                    assert result.status_code == 200
                    
                    # Only valid file should be processed
                    assert mock_ocr.call_count == 1
                    assert mock_generate.call_count == 1
    
    @pytest.mark.asyncio
    async def test_upload_file_all_invalid_types(self, mock_request, mock_db_session):
        """Test uploading only invalid file types."""
        # Arrange
        mock_files = [Mock(spec=UploadFile), Mock(spec=UploadFile)]
        mock_files[0].filename = "document.pdf"
        mock_files[1].filename = "spreadsheet.xlsx"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_file(mock_files, mock_request, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "No valid files were processed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_file_ocr_processing_error(self, mock_request, mock_db_session):
        """Test handling OCR processing errors."""
        # Arrange
        mock_files = [Mock(spec=UploadFile)]
        mock_files[0].filename = "test.jpg"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            mock_ocr.side_effect = Exception("OCR processing failed")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await upload_file(mock_files, mock_request, mock_db_session)
            
            assert exc_info.value.status_code == 400
            assert "No valid files were processed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_file_no_valid_dot_readings(self, mock_request, mock_db_session):
        """Test uploading files that don't contain valid DOT readings."""
        # Arrange
        mock_files = [Mock(spec=UploadFile)]
        mock_files[0].filename = "test.jpg"
        
        mock_ocr_record = Mock()
        mock_ocr_record.dot_reading = None  # No valid DOT reading
        
        mock_ocr_result = Mock()
        mock_ocr_result.id = 1
        mock_ocr_result.dot_reading = None
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
                        
                        mock_ocr.return_value = "NO DOT NUMBER FOUND"
                        mock_generate.return_value = mock_ocr_record
                        mock_save_ocr.return_value = [mock_ocr_result]
                        
                        # Act
                        result = await upload_file(mock_files, mock_request, mock_db_session)
                        
                        # Assert
                        assert isinstance(result, JSONResponse)
                        assert result.status_code == 200
                        
                        # OCR should be processed but no SAFER lookup
                        mock_ocr.assert_called_once()
                        mock_generate.assert_called_once()
                        mock_safer.assert_not_called()
                        mock_save_ocr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_file_orphan_dot_reading(self, mock_request, mock_db_session):
        """Test handling orphan DOT reading (0000000)."""
        # Arrange
        mock_files = [Mock(spec=UploadFile)]
        mock_files[0].filename = "test.jpg"
        
        mock_ocr_record = Mock()
        mock_ocr_record.dot_reading = "0000000"  # Orphan record
        
        mock_ocr_result = Mock()
        mock_ocr_result.id = 1
        mock_ocr_result.dot_reading = "0000000"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
                        
                        mock_ocr.return_value = "USDOT 0000000"
                        mock_generate.return_value = mock_ocr_record
                        mock_save_ocr.return_value = [mock_ocr_result]
                        
                        # Act
                        result = await upload_file(mock_files, mock_request, mock_db_session)
                        
                        # Assert
                        assert isinstance(result, JSONResponse)
                        assert result.status_code == 200
                        
                        # Should not perform SAFER lookup for orphan records
                        mock_safer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_upload_file_safer_lookup_failure(self, mock_request, mock_db_session):
        """Test handling SAFER lookup failures."""
        # Arrange
        mock_files = [Mock(spec=UploadFile)]
        mock_files[0].filename = "test.jpg"
        
        mock_ocr_record = Mock()
        mock_ocr_record.dot_reading = "123456"
        
        mock_ocr_result = Mock()
        mock_ocr_result.id = 1
        mock_ocr_result.dot_reading = "123456"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.safer_web_lookup_from_dot') as mock_safer:
                    with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                        
                        mock_ocr.return_value = "USDOT 123456 TEST CARRIER"
                        mock_generate.return_value = mock_ocr_record
                        
                        mock_safer_data = Mock()
                        mock_safer_data.lookup_success_flag = False  # Lookup failed
                        mock_safer.return_value = mock_safer_data
                        
                        mock_save_ocr.return_value = [mock_ocr_result]
                        
                        # Act
                        result = await upload_file(mock_files, mock_request, mock_db_session)
                        
                        # Assert
                        assert isinstance(result, JSONResponse)
                        assert result.status_code == 200
                        
                        # SAFER lookup should be attempted but no carrier data saved
                        mock_safer.assert_called_once()
                        mock_save_ocr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_file_mixed_file_types(self, mock_request, mock_db_session):
        """Test uploading a mix of valid and invalid file types."""
        # Arrange
        mock_files = []
        valid_extensions = [".jpg", ".png", ".bmp", ".heic"]
        invalid_extensions = [".pdf", ".txt", ".doc"]
        
        # Create mix of valid and invalid files
        for i, ext in enumerate(valid_extensions + invalid_extensions):
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = f"file{i}{ext}"
            mock_files.append(mock_file)
        
        mock_ocr_records = [Mock() for _ in range(len(valid_extensions))]
        for i, record in enumerate(mock_ocr_records):
            record.dot_reading = f"12345{i}"
        
        mock_ocr_results = [Mock() for _ in range(len(valid_extensions))]
        for i, result in enumerate(mock_ocr_results):
            result.id = i + 1
            result.dot_reading = f"12345{i}"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    
                    mock_ocr.return_value = "USDOT 123456 TEST CARRIER"
                    mock_generate.side_effect = mock_ocr_records
                    mock_save_ocr.return_value = mock_ocr_results
                    
                    # Act
                    result = await upload_file(mock_files, mock_request, mock_db_session)
                    
                    # Assert
                    assert isinstance(result, JSONResponse)
                    assert result.status_code == 200
                    
                    # Only valid files should be processed
                    assert mock_ocr.call_count == len(valid_extensions)
                    assert mock_generate.call_count == len(valid_extensions)
    
    @pytest.mark.asyncio
    async def test_upload_file_session_data_extraction(self, mock_db_session):
        """Test that user and org IDs are correctly extracted from session."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {
            'userinfo': {
                'sub': 'custom_user_id',
                'org_id': 'custom_org_id'
            }
        }
        
        mock_files = [Mock(spec=UploadFile)]
        mock_files[0].filename = "test.jpg"
        
        mock_ocr_record = Mock()
        mock_ocr_record.dot_reading = "123456"
        
        mock_ocr_result = Mock()
        mock_ocr_result.id = 1
        mock_ocr_result.dot_reading = "123456"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    
                    mock_ocr.return_value = "USDOT 123456"
                    mock_generate.return_value = mock_ocr_record
                    mock_save_ocr.return_value = [mock_ocr_result]
                    
                    # Act
                    result = await upload_file(mock_files, mock_request, mock_db_session)
                    
                    # Assert
                    assert isinstance(result, JSONResponse)
                    assert result.status_code == 200
                    
                    # Verify the OCRResultCreate was called with correct user/org IDs
                    mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_file_default_org_id(self, mock_db_session):
        """Test that org_id defaults to user_id when not in session."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {
            'userinfo': {
                'sub': 'user_without_org'
                # No org_id in session
            }
        }
        
        mock_files = [Mock(spec=UploadFile)]
        mock_files[0].filename = "test.jpg"
        
        mock_ocr_record = Mock()
        mock_ocr_record.dot_reading = "123456"
        
        mock_ocr_result = Mock()
        mock_ocr_result.id = 1
        mock_ocr_result.dot_reading = "123456"
        
        with patch('app.routes.upload.cloud_ocr_from_image_file', new_callable=AsyncMock) as mock_ocr:
            with patch('app.routes.upload.generate_dot_record') as mock_generate:
                with patch('app.routes.upload.save_ocr_results_bulk') as mock_save_ocr:
                    
                    mock_ocr.return_value = "USDOT 123456"
                    mock_generate.return_value = mock_ocr_record
                    mock_save_ocr.return_value = [mock_ocr_result]
                    
                    # Act
                    result = await upload_file(mock_files, mock_request, mock_db_session)
                    
                    # Assert
                    assert isinstance(result, JSONResponse)
                    assert result.status_code == 200