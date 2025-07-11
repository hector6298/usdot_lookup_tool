"""
Unit tests for auth routes.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.routes.auth import (
    login,
    signup,
    logout,
    callback,
    verify_login,
    verify_login_json_response
)


class TestLogin:
    """Test login route."""
    
    @pytest.mark.asyncio
    async def test_login_not_authenticated(self):
        """Test login when user is not authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {}  # No id_token
        mock_request.url_for.return_value = "http://localhost:8000/callback"
        
        mock_oauth = Mock()
        mock_oauth.auth0.authorize_redirect = AsyncMock(return_value=RedirectResponse("http://auth0.com/login"))
        
        with patch('app.routes.auth.oauth', mock_oauth):
            with patch.dict('os.environ', {'ENVIRONMENT': 'prod'}):
                # Act
                result = await login(mock_request)
                
                # Assert
                mock_oauth.auth0.authorize_redirect.assert_called_once_with(
                    mock_request,
                    redirect_uri="http://localhost:8000/callback"
                )
    
    @pytest.mark.asyncio
    async def test_login_already_authenticated(self):
        """Test login when user is already authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {'id_token': 'existing_token'}
        mock_request.url_for.return_value = "http://localhost:8000/dashboard/carriers"
        
        # Act
        result = await login(mock_request)
        
        # Assert
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 307
    
    @pytest.mark.asyncio 
    async def test_login_dev_environment_with_ngrok(self):
        """Test login in dev environment with NGROK tunnel."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {}
        
        mock_oauth = Mock()
        mock_oauth.auth0.authorize_redirect = AsyncMock(return_value=RedirectResponse("http://auth0.com/login"))
        
        with patch('app.routes.auth.oauth', mock_oauth):
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'dev',
                'NGROK_TUNNEL_URL': 'https://abc123.ngrok.io'
            }):
                # Act
                result = await login(mock_request)
                
                # Assert
                mock_oauth.auth0.authorize_redirect.assert_called_once_with(
                    mock_request,
                    redirect_uri="https://abc123.ngrok.io/callback"
                )


class TestSignup:
    """Test signup route."""
    
    @pytest.mark.asyncio
    async def test_signup_not_authenticated(self):
        """Test signup when user is not authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {}
        mock_request.url_for.return_value = "http://localhost:8000/callback"
        
        mock_oauth = Mock()
        mock_oauth.auth0.authorize_redirect = AsyncMock(return_value=RedirectResponse("http://auth0.com/signup"))
        
        with patch('app.routes.auth.oauth', mock_oauth):
            with patch.dict('os.environ', {'ENVIRONMENT': 'prod'}):
                # Act
                result = await signup(mock_request)
                
                # Assert
                mock_oauth.auth0.authorize_redirect.assert_called_once_with(
                    mock_request,
                    redirect_uri="http://localhost:8000/callback",
                    screen_hint="signup"
                )
    
    @pytest.mark.asyncio
    async def test_signup_already_authenticated(self):
        """Test signup when user is already authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {'id_token': 'existing_token'}
        mock_request.url_for.return_value = "http://localhost:8000/dashboard/carriers"
        
        # Act
        result = await signup(mock_request)
        
        # Assert
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 307


class TestLogout:
    """Test logout route."""
    
    def test_logout_with_salesforce_connection(self):
        """Test logout when user is connected to Salesforce."""
        # Arrange
        mock_request = Mock()
        mock_session = Mock()
        mock_session.__getitem__ = Mock(return_value=True)  # sf_connected = True
        mock_session.__contains__ = Mock(return_value=True)
        mock_request.session = mock_session
        mock_request.url_for.return_value = "http://localhost:8000/"
        
        with patch('app.routes.auth.disconnect_salesforce') as mock_disconnect:
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'prod',
                'AUTH0_DOMAIN': 'test.auth0.com',
                'AUTH0_CLIENT_ID': 'test_client_id'
            }):
                # Act
                result = logout(mock_request)
                
                # Assert
                mock_disconnect.assert_called_once_with(mock_request)
                mock_session.clear.assert_called_once()
                assert isinstance(result, RedirectResponse)
    
    def test_logout_without_salesforce_connection(self):
        """Test logout when user is not connected to Salesforce."""
        # Arrange
        mock_request = Mock()
        mock_session = Mock()
        mock_session.__contains__ = Mock(return_value=False)  # No sf_connected key
        mock_request.session = mock_session
        mock_request.url_for.return_value = "http://localhost:8000/"
        
        with patch('app.routes.auth.disconnect_salesforce') as mock_disconnect:
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'prod',
                'AUTH0_DOMAIN': 'test.auth0.com',
                'AUTH0_CLIENT_ID': 'test_client_id'
            }):
                # Act
                result = logout(mock_request)
                
                # Assert
                mock_disconnect.assert_not_called()
                mock_session.clear.assert_called_once()
                assert isinstance(result, RedirectResponse)
    
    def test_logout_dev_environment_with_ngrok(self):
        """Test logout in dev environment with NGROK tunnel."""
        # Arrange
        mock_request = Mock()
        mock_session = Mock()
        mock_session.__contains__ = Mock(return_value=False)
        mock_request.session = mock_session
        
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'dev',
            'NGROK_TUNNEL_URL': 'https://abc123.ngrok.io',
            'AUTH0_DOMAIN': 'test.auth0.com',
            'AUTH0_CLIENT_ID': 'test_client_id'
        }):
            # Act
            result = logout(mock_request)
            
            # Assert
            assert isinstance(result, RedirectResponse)
            assert "abc123.ngrok.io" in str(result.headers["Location"])
    
    def test_logout_constructs_auth0_url_correctly(self):
        """Test that logout constructs the Auth0 logout URL correctly."""
        # Arrange
        mock_request = Mock()
        mock_session = Mock()
        mock_session.__contains__ = Mock(return_value=False)
        mock_request.session = mock_session
        mock_request.url_for.return_value = "http://localhost:8000/"
        
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'prod',
            'AUTH0_DOMAIN': 'test.auth0.com',
            'AUTH0_CLIENT_ID': 'test_client_id'
        }):
            # Act
            result = logout(mock_request)
            
            # Assert
            assert isinstance(result, RedirectResponse)
            assert "test.auth0.com/v2/logout" in str(result.headers["Location"])
            assert "localhost%3A8000" in str(result.headers["Location"])
            assert "client_id=test_client_id" in str(result.headers["Location"])


class TestCallback:
    """Test callback route."""
    
    @pytest.mark.asyncio
    async def test_callback_success(self, mock_db_session):
        """Test successful OAuth callback processing."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {}
        mock_request.url_for.return_value = "http://localhost:8000/dashboard/carriers"
        
        mock_token = {
            'id_token': 'test_id_token',
            'userinfo': {
                'sub': 'test_user_123',
                'email': 'test@example.com'
            }
        }
        
        mock_oauth = Mock()
        mock_oauth.auth0.authorize_access_token = AsyncMock(return_value=mock_token)
        
        with patch('app.routes.auth.oauth', mock_oauth):
            with patch('app.routes.auth.save_user_org_membership') as mock_save:
                # Act
                result = await callback(mock_request, mock_db_session)
                
                # Assert
                assert mock_request.session['id_token'] == 'test_id_token'
                assert mock_request.session['userinfo'] == mock_token['userinfo']
                mock_save.assert_called_once_with(mock_db_session, mock_token)
                assert isinstance(result, RedirectResponse)
    
    @pytest.mark.asyncio
    async def test_callback_token_error(self, mock_db_session):
        """Test callback when token authorization fails."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {}
        
        mock_oauth = Mock()
        mock_oauth.auth0.authorize_access_token = AsyncMock(side_effect=Exception("Token error"))
        
        with patch('app.routes.auth.oauth', mock_oauth):
            # Act & Assert
            with pytest.raises(Exception, match="Token error"):
                await callback(mock_request, mock_db_session)


class TestVerifyLogin:
    """Test verify_login dependency."""
    
    def test_verify_login_authenticated(self, mock_auth_session):
        """Test verify_login when user is authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = mock_auth_session
        
        # Act & Assert - Should not raise exception
        result = verify_login(mock_request)
        assert result is None
    
    def test_verify_login_not_authenticated(self, mock_unauthenticated_session):
        """Test verify_login when user is not authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = mock_unauthenticated_session
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_login(mock_request)
        
        assert exc_info.value.status_code == 307
        assert exc_info.value.headers["Location"] == "/login"
    
    def test_verify_login_partial_session(self):
        """Test verify_login with partial session data."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {'userinfo': {'sub': 'test'}}  # Has userinfo but no id_token
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_login(mock_request)
        
        assert exc_info.value.status_code == 307
        assert exc_info.value.headers["Location"] == "/login"


class TestVerifyLoginJsonResponse:
    """Test verify_login_json_response dependency."""
    
    def test_verify_login_json_response_authenticated(self, mock_auth_session):
        """Test verify_login_json_response when user is authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = mock_auth_session
        
        # Act
        result = verify_login_json_response(mock_request)
        
        # Assert - Should return None for authenticated users
        assert result is None
    
    def test_verify_login_json_response_not_authenticated(self, mock_unauthenticated_session):
        """Test verify_login_json_response when user is not authenticated."""
        # Arrange
        mock_request = Mock()
        mock_request.session = mock_unauthenticated_session
        
        # Act
        result = verify_login_json_response(mock_request)
        
        # Assert
        assert result.status_code == 403
        # Note: The current implementation has a bug - it returns JSONResponse instead of raising HTTPException
    
    def test_verify_login_json_response_partial_session(self):
        """Test verify_login_json_response with partial session data."""
        # Arrange
        mock_request = Mock()
        mock_request.session = {'userinfo': {'sub': 'test'}}  # Has userinfo but no id_token
        
        # Act
        result = verify_login_json_response(mock_request)
        
        # Assert
        assert result.status_code == 403