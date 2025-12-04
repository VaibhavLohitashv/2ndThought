## Existing Content
This is the existing content of the README file that provides an overview of the project.

---

# Realtime Forum

This repository contains a simple realtime forum application with a FastAPI backend and an Angular frontend. The project supports running locally (native Python/Node) and using Docker Compose for a reproducible development environment.

---

**Contents**

- `backend/` — FastAPI backend, Alembic migrations, and configuration
- `frontend/` — Angular frontend
- `docker-compose.yml` — Compose file to run Postgres, Redis, backend and frontend
- `backend/.env` — Environment file used by the backend in development

---

## Prerequisites (local)

- Python 3.10+ (for backend)
- Node.js 20+ and npm (for frontend build & dev server)
- PostgreSQL (if running DB locally)
- Redis (if running locally)

## Run Locally (recommended for development)

### Backend (native)

1. Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r backend/requirements.txt
```

3. Copy `backend/.env` and adjust values if you need to run Postgres/Redis locally. Example keys included in `backend/.env`:

```text
DB_HOST=localhost
DB_PORT=5432
DB_USER=forum
DB_PASSWORD=forum
DB_NAME=forum_db

SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

GOOGLE_APPLICATION_CREDENTIALS=discussion-forum-a7895-firebase-adminsdk-fbsvc-15ca88afde.json
FIREBASE_PROJECT_ID=discussion-forum-a7895

REDIS_URL=redis://localhost:6379
```

4. Start local Postgres and Redis (if not using Docker). Create the `forum_db` database and user matching the `.env` values.

5. Apply alembic migrations:

```powershell
# from repository root
cd backend
alembic upgrade head
```

6. Run the backend:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (native)

1. Install dependencies and run dev server:

```powershell
cd frontend
npm install
npm start
```

2. The Angular dev server runs on `http://localhost:4200`. The frontend expects the API at `http://localhost:8000` by default (see `frontend/src/environments/environment.ts`).

---

## Run with Docker Compose (recommended for consistent dev environment)

The repository contains a `docker-compose.yml` that runs:
- `db` (Postgres)
- `redis` (Redis)
- `backend` (builds `./backend` image)
- `frontend` (builds `./frontend` image)

### Build and start all services

```powershell
# from repository root
docker-compose up -d --build
```

### Apply migrations (required once per fresh DB)

The backend reads `backend/.env` via the Compose `env_file`. When running in Docker the DB host should be `db` (the service name). To run migrations using the backend container:

```powershell
# run alembic inside the backend container
docker-compose exec backend alembic upgrade head
```

If you prefer to run migrations before starting the backend service:

```powershell
docker-compose up -d db redis
# wait for Postgres to be ready
docker-compose run --rm backend alembic upgrade head
docker-compose up -d backend frontend
```

### Useful docker-compose commands

```powershell
# show running containers
docker-compose ps

# view logs (all services)
docker-compose logs -f

# view logs for a specific service
docker-compose logs -f backend

# stop and remove containers, networks, volumes created by compose
docker-compose down
```

---

## Environment and secrets

- `backend/.env` contains the default development environment values. In Docker Compose the backend uses `env_file: ./backend/.env` and additionally overrides `DB_HOST=db` and `REDIS_URL=redis://redis:6379` so the container connects to the Compose services.
- The Firebase credentials JSON file `backend/discussion-forum-a7895-firebase-adminsdk-fbsvc-15ca88afde.json` is mounted into the backend container at `/secrets/firebase.json` and `GOOGLE_APPLICATION_CREDENTIALS` is set to this path in the compose file. If you want to avoid a host bind mount, consider using Docker secrets or a secret manager.

### Keep secrets secure

- Do not check real production secrets into source control.
- For production consider using Docker secrets, environment variables set by your CI, or a secrets manager like AWS Secrets Manager / Azure Key Vault.

---

## Troubleshooting

- Frontend not accessible from host
	- The Angular dev server binds to `localhost` by default. The Compose `frontend` service is configured to run `ng serve --host 0.0.0.0 --port 4200` so it binds to all interfaces inside the container and Compose maps the container `4200` to the host `4200`. If you cannot access `http://localhost:4200`:
		- Ensure the container is running: `docker-compose ps`.
		- Check logs: `docker-compose logs frontend --tail=200`.
		- Test with curl from host: `curl http://localhost:4200 -UseBasicParsing` (PowerShell).
		- Check firewall/antivirus or proxies that might block the port.

- Backend fails with missing env vars
	- Ensure `backend/.env` exists and Compose `env_file` is present. The backend `Settings` uses Pydantic and requires several fields; supplying them via the `.env` file or `environment` in Compose fixes missing-field errors.

- Alembic/DB connection errors
	- Ensure Postgres is ready before running migrations. You can wait a few seconds or retry the `alembic upgrade head` command until it connects.

---

## Optional improvements (ideas)

- Run `alembic upgrade head` automatically from the backend entrypoint with a wait-and-retry loop.
- Use Docker secrets for `SECRET_KEY` and DB password.
- Add healthchecks for `db` and `backend` services in `docker-compose.yml`.

---

If you want, I can implement automatic migrations on backend startup and add healthchecks — tell me which you prefer and I'll add the changes.

