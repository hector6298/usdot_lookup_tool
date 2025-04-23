from sqlmodel import Session, SQLModel, create_engine
import os

# Database connection settings
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    raise EnvironmentError(f"One or more required environment variables are not set. {DB_USER}, {DB_PASSWORD}, {DB_HOST}, {DB_PORT}, {DB_NAME}")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create engine and session
engine = create_engine(DATABASE_URL)

def get_db():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session

def init_db():
    """Initialize the database."""
    SQLModel.metadata.create_all(bind=engine)
    print("Database initialized.")

if __name__ == "__main__":
    print(DATABASE_URL)
    init_db()
