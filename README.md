# Truck Carrier Lookups for lead generation in truck rentals

A FastAPI application for processing images, extracting USDOT numbers using OCR, and storing the results in a PostgreSQL database.

---

## ✅ Features
- 📸 Upload images for OCR processing.  
- 🔍 Extract **USDOT numbers** from the image text.  
- 🛠️ Store and retrieve OCR results from a PostgreSQL database.  
- ⚙️ Bulk insert and update operations for efficiency.  
- 🗜️ **Client-side image compression** before uploading to reduce latency.  

---

## 🛠️ Technologies Used
- **Backend:** FastAPI, SQLAlchemy, SQLModel  
- **Frontend:** HTML, JavaScript, Jinja2  
- **Database:** PostgreSQL  
- **OCR:** Google Cloud OCR API  
- **Docker:** Containerized services with Docker Compose  

---

## 📁 Project Structure
```
/app
 ├── static/              # Static files (JS, CSS)
 │    ├── upload.js        # Image upload & compression logic
 ├── templates/           # HTML templates
 │    └── home.html        # Main frontend page
 |    └── dot_carrier_details.html
 ├── app/                 # FastAPI backend
 │    ├── crud.py          # Database operations
 │    ├── models.py        # SQLAlchemy models
 │    ├── database.py      # DB connection
 │    ├── main.py          # FastAPI app entry point
 |    ├── info_extraction.py
 |    └── config.py
 ├── Dockerfile            # Docker build config for FastAPI app
 ├── docker-compose.yml    # Docker Compose setup
 ├── requirements.txt      # Python dependencies
 ├── README.md             # Project documentation
```

---

## ⚙️ Setup and Installation

### 🔥 1. Clone the Repository
```bash
git clone <your-repo-url>
cd doj_ocr_webapp
```

### 🐋 4. Start the Docker Containers
Run the following command to start the FastAPI app and PostgreSQL database:
```bash
docker-compose up --build
```

- FastAPI will be available at:  
  👉 `http://localhost:8000`

- Documentation (Swagger UI) at:  
  👉 `http://localhost:8000/docs`

---

## 🚀 Usage

1. **Open the app** in your browser:  
   👉 `http://localhost:8000`

2. **Upload images** for OCR processing.

3. **View results** in the results table.



## 🛠️ Environment Variables
Create a `.env` file to store the environment variables:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/ocr_db
```

---
