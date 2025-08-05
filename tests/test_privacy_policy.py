import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os

def test_privacy_policy_route():
    """Test that privacy policy route can be imported and works."""
    # Mock environment variables to avoid database connection
    with patch.dict(os.environ, {
        'DB_USER': 'test',
        'DB_PASSWORD': 'test',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test',
        'WEBAPP_SESSION_SECRET': 'test-secret'
    }):
        # Mock the database init to avoid actual DB connection
        with patch('app.database.init_db'):
            from app.main import app
            client = TestClient(app)
            
            # Test that the privacy policy endpoint returns 200
            response = client.get("/privacy-policy")
            assert response.status_code == 200
            assert "Privacy Policy" in response.text
            assert "DotAI" in response.text
            assert "hectormrejia@gmail.com" in response.text

def test_privacy_policy_content():
    """Test that privacy policy contains expected content."""
    with patch.dict(os.environ, {
        'DB_USER': 'test',
        'DB_PASSWORD': 'test', 
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test',
        'WEBAPP_SESSION_SECRET': 'test-secret'
    }):
        with patch('app.database.init_db'):
            from app.main import app
            client = TestClient(app)
            
            response = client.get("/privacy-policy")
            content = response.text
            
            # Check for key sections of privacy policy
            assert "Information We Collect" in content
            assert "How We Use Your Information" in content
            assert "Third-Party Services" in content
            assert "Data Security" in content
            assert "Contact Us" in content
            assert "Stripe" in content  # Payment processor mention