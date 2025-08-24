"""
Test the SEO routes (sitemap.xml and robots.txt)
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routes import seo

# Create a minimal FastAPI app for testing SEO routes only
def create_test_app():
    app = FastAPI(title="Test App")
    app.include_router(seo.router)
    return app

def test_sitemap_xml():
    """Test that sitemap.xml is generated correctly."""
    app = create_test_app()
    client = TestClient(app)
    response = client.get("/sitemap.xml")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml; charset=utf-8"
    
    content = response.text
    assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in content
    assert "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" in content
    assert "<loc>http://testserver/</loc>" in content
    assert "<loc>http://testserver/blog</loc>" in content
    assert "<loc>http://testserver/blog/automated-lead-capture-pipeline</loc>" in content
    assert "<loc>http://testserver/privacy-policy</loc>" in content
    assert "<loc>http://testserver/team-request</loc>" in content

def test_robots_txt():
    """Test that robots.txt is generated correctly."""
    app = create_test_app()
    client = TestClient(app)
    response = client.get("/robots.txt")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    
    content = response.text
    assert "User-agent: *" in content
    assert "Allow: /" in content
    assert "Allow: /blog" in content
    assert "Disallow: /dashboards/" in content
    assert "Disallow: /data/" in content
    assert "Disallow: /login" in content
    assert "Sitemap: http://testserver/sitemap.xml" in content

def test_sitemap_xml_contains_required_elements():
    """Test that sitemap.xml contains all required SEO elements."""
    app = create_test_app()
    client = TestClient(app)
    response = client.get("/sitemap.xml")
    
    content = response.text
    # Check for required sitemap elements
    assert "<priority>1.0</priority>" in content  # Home page priority
    assert "<changefreq>weekly</changefreq>" in content
    assert "<lastmod>" in content
    
def test_robots_txt_disallows_private_areas():
    """Test that robots.txt properly disallows private/authenticated areas."""
    app = create_test_app()
    client = TestClient(app)
    response = client.get("/robots.txt")
    
    content = response.text
    # Ensure sensitive areas are disallowed
    assert "Disallow: /dashboards/" in content
    assert "Disallow: /data/" in content
    assert "Disallow: /upload" in content
    assert "Disallow: /salesforce/" in content