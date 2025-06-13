# Database migrations for DOT OCR App

## Generate Alembic structure
docker compose exec web alembic init migrations

## Create initial migration script
docker compose exec web alembic revision --autogenerate -m "Initial migration"

## Apply the migration to the database
docker compose exec web alembic upgrade head

docker compose exec web alembic history