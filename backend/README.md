Local development
---------------

The backend expects the following environment variables (see `.env.example`). For quick local development you can run Postgres and Redis with Docker Compose from the repository root:

```powershell
docker-compose up -d db redis
```

The provided `.env` in this repo is configured to connect to services on `localhost` (Postgres `5432`, Redis `6379`) using the credentials that match `docker-compose.yml`.

If you run the backend inside a container (for example by `docker-compose up` for all services), set `DB_HOST=db` and `REDIS_URL=redis://redis:6379` instead so the container network names are used.

If you changed `.env` values, restart the backend so the new settings are picked up.
