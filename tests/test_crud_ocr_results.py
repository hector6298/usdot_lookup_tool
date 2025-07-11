"""
Unit tests for OCR results CRUD operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from app.crud.ocr_results import (
    save_ocr_results_bulk,
    save_single_ocr_result,
    get_ocr_result_by_id,
    get_ocr_results
)
from app.models.ocr_results import OCRResult, OCRResultCreate


class TestSaveOcrResultsBulk:
    """Test save_ocr_results_bulk function."""
    
    def test_save_ocr_results_bulk_success(self, mock_db_session):
        """Test bulk saving OCR results successfully."""
        # Arrange
        mock_results = [Mock(spec=OCRResult) for _ in range(3)]
        for i, result in enumerate(mock_results):
            result.id = i + 1
        
        # Act
        result = save_ocr_results_bulk(mock_db_session, mock_results)
        
        # Assert
        assert result == mock_results
        mock_db_session.add_all.assert_called_once_with(mock_results)
        mock_db_session.commit.assert_called_once()
        assert mock_db_session.refresh.call_count == 3
    
    def test_save_ocr_results_bulk_empty_list(self, mock_db_session):
        """Test bulk saving with empty list."""
        # Arrange
        empty_results = []
        
        # Act
        result = save_ocr_results_bulk(mock_db_session, empty_results)
        
        # Assert
        assert result == []
        mock_db_session.add_all.assert_not_called()
        mock_db_session.commit.assert_not_called()
    
    def test_save_ocr_results_bulk_database_error(self, mock_db_session):
        """Test handling database errors in bulk save."""
        # Arrange
        mock_results = [Mock(spec=OCRResult)]
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            save_ocr_results_bulk(mock_db_session, mock_results)
        
        assert exc_info.value.status_code == 500
        assert "Database error" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()


class TestSaveSingleOcrResult:
    """Test save_single_ocr_result function."""
    
    def test_save_single_ocr_result_success(self, mock_db_session, sample_ocr_db_record):
        """Test saving single OCR result successfully."""
        # Arrange
        sample_ocr_db_record.id = 1
        
        # Act
        result = save_single_ocr_result(mock_db_session, sample_ocr_db_record)
        
        # Assert
        assert result == sample_ocr_db_record
        mock_db_session.add.assert_called_once_with(sample_ocr_db_record)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(sample_ocr_db_record)
    
    def test_save_single_ocr_result_database_error(self, mock_db_session, sample_ocr_db_record):
        """Test handling database errors in single save."""
        # Arrange
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            save_single_ocr_result(mock_db_session, sample_ocr_db_record)
        
        assert exc_info.value.status_code == 500
        assert "Database error" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()


class TestGetOcrResultById:
    """Test get_ocr_result_by_id function."""
    
    def test_get_ocr_result_by_id_found(self, mock_db_session, sample_ocr_db_record):
        """Test getting OCR result by ID when it exists."""
        # Arrange
        result_id = 1
        sample_ocr_db_record.id = result_id
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_ocr_db_record
        
        # Act
        result = get_ocr_result_by_id(mock_db_session, result_id)
        
        # Assert
        assert result == sample_ocr_db_record
        mock_db_session.query.assert_called_once_with(OCRResult)
    
    def test_get_ocr_result_by_id_not_found(self, mock_db_session):
        """Test getting OCR result by ID when it doesn't exist."""
        # Arrange
        result_id = 999
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = get_ocr_result_by_id(mock_db_session, result_id)
        
        # Assert
        assert result is None
        mock_db_session.query.assert_called_once_with(OCRResult)


class TestGetOcrResults:
    """Test get_ocr_results function."""
    
    def test_get_ocr_results_no_filters(self, mock_db_session):
        """Test getting OCR results without any filters."""
        # Arrange
        mock_results = [Mock(spec=OCRResult) for _ in range(3)]
        mock_query = mock_db_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_results
        
        # Act
        result = get_ocr_results(mock_db_session)
        
        # Assert
        assert result == mock_results
        mock_db_session.query.assert_called_once_with(OCRResult)
        # Should filter for valid DOT only by default
        mock_query.filter.assert_called_once()
    
    def test_get_ocr_results_with_org_filter(self, mock_db_session):
        """Test getting OCR results filtered by org_id."""
        # Arrange
        org_id = "test_org_123"
        mock_results = [Mock(spec=OCRResult) for _ in range(2)]
        mock_query = mock_db_session.query.return_value
        
        # Setup sequential filter calls (both org_id and valid_dot_only filters)
        mock_query.filter.return_value = mock_query  # Return same query for chaining
        mock_query.order_by.return_value.all.return_value = mock_results
        
        # Act
        result = get_ocr_results(mock_db_session, org_id=org_id)
        
        # Assert
        assert result == mock_results
        # Should have two filter calls: org_id and valid_dot_only
        assert mock_query.filter.call_count == 2
    
    def test_get_ocr_results_with_pagination(self, mock_db_session):
        """Test getting OCR results with pagination."""
        # Arrange
        offset, limit = 10, 5
        mock_results = [Mock(spec=OCRResult) for _ in range(5)]
        mock_query = mock_db_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_results
        
        # Act
        result = get_ocr_results(mock_db_session, offset=offset, limit=limit)
        
        # Assert
        assert result == mock_results
        mock_query.filter.return_value.order_by.return_value.offset.assert_called_once_with(offset)
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.assert_called_once_with(limit)
    
    def test_get_ocr_results_include_invalid_dot(self, mock_db_session):
        """Test getting OCR results including invalid DOT readings."""
        # Arrange
        mock_results = [Mock(spec=OCRResult) for _ in range(3)]
        mock_query = mock_db_session.query.return_value
        mock_query.order_by.return_value.all.return_value = mock_results
        
        # Act
        result = get_ocr_results(mock_db_session, valid_dot_only=False)
        
        # Assert
        assert result == mock_results
        # Should not filter for valid DOT when valid_dot_only=False
        mock_query.filter.assert_not_called()
    
    def test_get_ocr_results_with_eager_loading(self, mock_db_session):
        """Test getting OCR results with eager loading of carrier data."""
        # Arrange
        mock_results = [Mock(spec=OCRResult) for _ in range(2)]
        mock_query = mock_db_session.query.return_value
        mock_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = mock_results
        
        # Act
        result = get_ocr_results(mock_db_session, eager_relations=True)
        
        # Assert
        assert result == mock_results
        mock_query.options.assert_called_once()
    
    def test_get_ocr_results_all_filters_combined(self, mock_db_session):
        """Test getting OCR results with all filters combined."""
        # Arrange
        org_id = "test_org_123"
        offset, limit = 5, 10
        mock_results = [Mock(spec=OCRResult) for _ in range(10)]
        mock_query = mock_db_session.query.return_value
        
        # Setup the sequential method calls
        mock_query.options.return_value = mock_query  # For eager loading
        mock_query.filter.return_value = mock_query   # For filters
        mock_query.order_by.return_value = mock_query # For ordering
        mock_query.offset.return_value = mock_query   # For pagination
        mock_query.limit.return_value = mock_query    # For pagination
        mock_query.all.return_value = mock_results
        
        # Act
        result = get_ocr_results(
            mock_db_session,
            org_id=org_id,
            offset=offset,
            limit=limit,
            valid_dot_only=True,
            eager_relations=True
        )
        
        # Assert
        assert result == mock_results
        mock_query.options.assert_called_once()
        # Should have calls for org filter and valid DOT filter
        assert mock_query.filter.call_count == 2
    
    def test_get_ocr_results_empty_result(self, mock_db_session):
        """Test getting OCR results when no results found."""
        # Arrange
        mock_query = mock_db_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        
        # Act
        result = get_ocr_results(mock_db_session)
        
        # Assert
        assert result == []
        mock_db_session.query.assert_called_once_with(OCRResult)