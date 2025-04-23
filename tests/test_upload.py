from fastapi.testclient import TestClient
from app.main import app
import io
from PIL import Image

client = TestClient(app)

def test_upload_file():
    # Create a simple black image for testing
    image = Image.new('RGB', (100, 100), color='black')
    img_bytes = io.BytesIO()
    image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {"file": ("test.png", img_bytes, "image/png")}
    response = client.post("/api/upload", files=files)
    
    assert response.status_code == 200
    assert "filename" in response.json()
    assert "extracted_text" in response.json()

