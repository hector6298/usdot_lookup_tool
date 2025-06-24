# DOJ OCR WebApp

## 🚚 What is This App?

**DOJ OCR WebApp** is a FastAPI-based application for processing truck images, extracting USDOT numbers using OCR, and managing carrier engagement data. It is designed for lead generation in truck rentals and logistics, allowing users to upload images, extract carrier information, and track engagement with carriers. The app supports multi-user organizations, engagement tracking, and data export, and is ready for deployment in cloud environments like Google Cloud Run.

---

## 📦 Features

- **Image Upload & OCR:** Upload truck images, extract USDOT numbers using Google Cloud OCR.
- **Carrier Data Management:** Store, filter, and export carrier and engagement data.
- **Engagement Tracking:** Track and update carrier engagement statuses (contacted, interested, etc.).
- **Infinite Scrolling:** Paginated data loading for large datasets.
- **CSV Export:** Download carrier and lookup data as CSV.
- **Multi-Org Support:** Engagement data is linked to organizations via `org_id`.
- **Authentication:** OAuth and session-based user management.

---

## 📝 Example Usage

1. **Login** or sign up.
2. **Upload** truck images to extract USDOT numbers.
3. **View and manage** carrier data in the dashboard.
4. **Track engagement** (contacted, interested, follow-up) with carriers.
5. **Export** your data as CSV for further analysis.

---

## 📁 Repository Structure

```
doj_ocr_webapp/
│
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry point
│   ├── models.py              # SQLModel ORM models
│   ├── crud.py                # Database operations
│   ├── database.py            # DB connection setup
│   ├── info_extraction.py     # OCR and text extraction logic
│   ├── auth_setup.py          # Authentication setup
│   ├── routes/                # FastAPI route modules
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   ├── data.py
│   │   ├── home.py
│   │   ├── upload.py
│   │   └── auth.py
│   ├── static/                # Static JS/CSS files
│   │   ├── filters_and_tables_render.js
│   │   ├── update_carrier_engagement.js
│   │   └── upload.js
│   └── templates/             # Jinja2 HTML templates
│       ├── base_dashboard.html
│       ├── dashboard.html
│       ├── dot_carrier_details.html
│       ├── home.html
│       └── lookup_history.html
│
├── migrations/                # Alembic migrations
│   ├── env.py
│   ├── versions/
│   └── README.md
│
├── Dockerfile                 # Docker build config
├── docker-compose.yml         # Docker Compose setup
├── requirements.txt           # Python dependencies
├── alembic.ini                # Alembic config
└── README.md                  # Project documentation
```

---

## 🌐 App Routes Overview

### **Frontend Pages**
- `/`  
  **Landing page** (static HTML, login/signup links)
- `/dashboards/carriers`  
  **Main dashboard** for carrier management, engagement, and OCR uploads
- `/dashboards/lookup_history`  
  **Lookup history** of OCR and carrier data
- `/dashboards/carrier_details/<usdot>`  
  **Carrier detail page** for a specific USDOT number

### **API Endpoints**
- `/upload`  
  **POST**: Upload images for OCR processing
- `/data/fetch/carriers`  
  **GET**: Fetch paginated carrier data (with filters)
- `/data/fetch/lookup_history`  
  **GET**: Fetch lookup/OCR history
- `/data/update/carrier_interests`  
  **POST**: Update carrier engagement statuses (contacted, interested, etc.)
- `/data/export/carriers`  
  **GET**: Export carrier data as CSV
- `/data/export/lookup_history`  
  **GET**: Export lookup history as CSV

### **Auth**
- `/login`, `/logout`  
  **User authentication** (OAuth, session-based)

---

## 🚀 Getting Started

### **1. Clone the Repository**
```bash
git clone <your-repo-url>
cd doj_ocr_webapp
```

### **2. Set Up Environment Variables**
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/ocr_db
WEBAPP_SESSION_SECRET=your_secret_key
GOOGLE_OCR_API_KEY=your_google_ocr_api_key
```

---

## 🐳 Build and Launch with Docker

### **1. Build and Start with Docker Compose**
```bash
docker-compose up --build
```
- This will build the FastAPI app and start the PostgreSQL database.
- The app will be available at [http://localhost:8000](http://localhost:8000)

### **2. Run Database Migrations**
```bash
docker-compose exec web alembic upgrade head
```
- This applies all Alembic migrations to set up the database schema.

---

## ☁️ Deploying to Google Cloud Run

1. **Build the Docker image:**
   ```bash
   docker build -t gcr.io/<your-project-id>/doj-ocr-webapp .
   ```

2. **Push to Google Container Registry:**
   ```bash
   docker push gcr.io/<your-project-id>/doj-ocr-webapp
   ```

3. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy doj-ocr-webapp \
     --image gcr.io/<your-project-id>/doj-ocr-webapp \
     --platform managed \
     --region <your-region> \
     --set-env-vars DATABASE_URL=postgresql://user:password@host:port/dbname,WEBAPP_SESSION_SECRET=your_secret_key,GOOGLE_OCR_API_KEY=your_google_ocr_api_key
   ```

4. **Run migrations in Cloud Run job or shell:**
   - Set the `DATABASE_URL` env variable.
   - Run: `alembic upgrade head`

---

## 🛠️ Development Tips

- **Static files** are served from static.
- **Templates** use Jinja2 and are in templates.
- **JS modules** handle table rendering, infinite scroll, and engagement tracking.
- **Alembic** is used for migrations; configure your DB URL via environment variables for cloud compatibility.
- **Logging** is set up in main.py for debugging and monitoring.
