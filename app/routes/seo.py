from fastapi import APIRouter, Request
from fastapi.responses import Response
from datetime import datetime

router = APIRouter()

@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(request: Request):
    """Generate XML sitemap for search engines."""
    base_url = str(request.base_url).rstrip('/')
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{base_url}/</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{base_url}/blog</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>{base_url}/blog/automated-lead-capture-pipeline</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>
    <url>
        <loc>{base_url}/privacy-policy</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.5</priority>
    </url>
    <url>
        <loc>{base_url}/team-request</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>
</urlset>"""
    
    return Response(
        content=sitemap_content,
        media_type="application/xml"
    )

@router.get("/robots.txt", response_class=Response)
async def robots_txt(request: Request):
    """Generate robots.txt file for search engine crawlers."""
    base_url = str(request.base_url).rstrip('/')
    
    robots_content = f"""User-agent: *
Allow: /
Allow: /blog
Allow: /blog/automated-lead-capture-pipeline
Allow: /privacy-policy
Allow: /team-request

# Disallow private/authenticated areas
Disallow: /dashboards/
Disallow: /data/
Disallow: /upload
Disallow: /login
Disallow: /signup
Disallow: /logout
Disallow: /salesforce/

# Sitemap location
Sitemap: {base_url}/sitemap.xml
"""
    
    return Response(
        content=robots_content,
        media_type="text/plain"
    )