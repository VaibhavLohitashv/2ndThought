# Realtime Forum

A realtime discussion forum application built with FastAPI backend and Angular frontend. Features include Firebase authentication, PostgreSQL database, Redis for notifications, WebSocket real-time updates, and Docker support for easy development and deployment.

## Author

Vaibhav Lohitashv

## Repository

- **GitHub**: [https://github.com/VaibhavLohitashv/2ndThought](https://github.com/VaibhavLohitashv/2ndThought)
- **Current Branch**: main

## Tech Stack

- **Backend**: FastAPI (Python), SQLAlchemy, Alembic (migrations), Pydantic
- **Frontend**: Angular, TypeScript
- **Database**: PostgreSQL
- **Cache/Notifications**: Redis
- **Authentication**: Firebase Auth
- **Real-time**: WebSockets
- **Containerization**: Docker, Docker Compose

## Project Structure

```
realtime-forum/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── auth/              # Firebase authentication
│   │   ├── core/              # Configuration, security, exceptions
│   │   ├── database/          # DB models and connection
│   │   ├── routes/            # API endpoints (posts, threads, users, WS)
│   │   ├── schemas/           # Pydantic schemas
│   │   └── utils/             # Redis notifications, WebSocket manager
│   ├── alembic/               # Database migrations
│   ├── scripts/               # Startup scripts
│   ├── static/                # Static files (images)
│   ├── tests/                 # Unit tests
│   ├── .env.example           # Environment template
│   ├── Dockerfile             # Backend container
│   ├── pyproject.toml         # Python dependencies
│   ├── requirements.txt       # Python requirements
│   └── README.md
├── frontend/                   # Angular frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/    # UI components (navbar, posts, etc.)
│   │   │   ├── guards/        # Route guards
│   │   │   ├── pages/         # Page components (login, profile, threads)
│   │   │   ├── services/      # Angular services
│   │   │   └── shared/        # Shared utilities
│   │   ├── environments/      # Environment configurations
│   │   └── ...
│   ├── Dockerfile             # Frontend container
│   ├── package.json           # Node dependencies
│   └── ...
├── docker-compose.yml         # Docker Compose configuration
└── README.md                  # This file
```

## Prerequisites

### For Local Development
- Python 3.10 or higher
- Node.js 20+ and npm
- PostgreSQL 13+ (if running locally)
- Redis 6+ (if running locally)

### For Docker Development
- Docker Engine
- Docker Compose

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/VaibhavLohitashv/2ndThought.git
   cd realtime-forum
   ```

2. **Set up environment variables** (see Environment Variables section below)

## Running the Application

### Option 1: Local Development (Recommended for active development)

#### Backend Setup

1. **Navigate to backend directory**:
   ```powershell
   cd backend
   ```

2. **Create and activate virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
   Or use uv if installed
   ```powershell
   uv sync
   ```

4. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Fill in your configuration values (see Environment Variables section)

5. **Set up database**:
   - Ensure PostgreSQL is running locally
   - Create database and user as specified in `.env`
   - Run migrations:
     ```powershell
     alembic upgrade head
     ```

6. **Start the backend server**:
   ```powershell
   uvicorn app.main:app --reload
   ```
   or
   ```powershell
   uv run uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. **Navigate to frontend directory** (in a new terminal):
   ```powershell
   cd frontend
   ```

2. **Install dependencies**:
   ```powershell
   npm install
   ```

3. **Start development server**:
   ```powershell
   npm start
   ```

4. **Access the application**:
   - Frontend: http://localhost:4200
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Option 2: Docker Compose (Recommended for consistent environment)

1. **Build and start all services**:
   ```powershell
   docker-compose up -d --build
   ```

2. **Run database migrations** (required for fresh database):
   ```powershell
   docker-compose exec backend alembic upgrade head
   ```

3. **Access the application**:
   - Frontend: http://localhost:4200
   - Backend API: http://localhost:8000
   - Database: localhost:5432 (from host)
   - Redis: localhost:6379 (from host)

#### Useful Docker Commands

```powershell
# View running containers
docker-compose ps

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend

# Stop and remove containers
docker-compose down

# Rebuild specific service
docker-compose up -d --build backend
```

## Environment Variables

### Backend Environment (.env)

Create `backend/.env` by copying `backend/.env.example` and configuring the following variables:

```dotenv
# Database Configuration
DB_HOST=localhost          # Host for PostgreSQL (use 'db' for Docker Compose)
DB_PORT=5432               # PostgreSQL port
DB_USER=forum              # Database username
DB_PASSWORD=forum          # Database password
DB_NAME=forum_db           # Database name

# JWT Authentication
SECRET_KEY=your-super-secret-key-change-in-production  # Random secret key for JWT
ALGORITHM=HS256           # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=30  # Token expiry in minutes

# Firebase Authentication
GOOGLE_APPLICATION_CREDENTIALS=discussion-forum-a7895-firebase-adminsdk-fbsvc-15ca88afde.json  # Path to Firebase service account JSON
FIREBASE_PROJECT_ID=discussion-forum-a7895  # Firebase project ID

# Redis Configuration
REDIS_URL=redis://localhost:6379  # Redis URL (use 'redis://redis:6379' for Docker Compose)
```

### Frontend Environment

The frontend uses TypeScript files in `frontend/src/environments/`:

**Development** (`environment.ts`):
```typescript
const firebaseConfig = {
  apiKey: 'your-firebase-api-key',
  authDomain: 'your-project.firebaseapp.com',
  projectId: 'your-project-id',
  storageBucket: 'your-project.firebasestorage.app',
  messagingSenderId: 'your-sender-id',
  appId: 'your-app-id',
  measurementId: 'your-measurement-id'
};

export const environment = {
  production: false,
  firebase: firebaseConfig,
  apiUrl: 'http://localhost:8000',    // Backend API URL
  wsUrl: 'ws://localhost:8000'        // WebSocket URL
};
```

**Production** (`environment.prod.ts`):
```typescript
const firebaseConfig = {
  // Same Firebase config as development
};

export const environment = {
  production: true,
  firebase: firebaseConfig,
  apiUrl: '/api',     // Relative API URL for production
  wsUrl: '/ws'        // Relative WebSocket URL for production
};
```

## Files Ignored by Git (.gitignore)

The following files and directories are ignored by Git and must be created locally:

- `backend/.env` - Backend environment variables (copy from `.env.example`)
- `backend/discussion-forum-a7895-firebase-adminsdk-fbsvc-15ca88afde.json` - Firebase service account credentials (download from Firebase Console)
- `backend/.venv/` - Python virtual environment
- `backend/__pycache__/` - Python bytecode cache
- `backend/.pytest_cache/` - Pytest cache
- `frontend/node_modules/` - Node.js dependencies
- `frontend/.angular/` - Angular build cache
- `*.log` - Log files
- `.DS_Store` - macOS system files

## API Endpoints

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

Key endpoints:
- `GET /api/threads` - List discussion threads
- `POST /api/threads` - Create new thread
- `GET /api/threads/{id}/posts` - Get posts in a thread
- `POST /api/posts` - Create new post
- `WebSocket /ws/{thread_id}` - Real-time updates for threads

## Testing

### Backend Tests
```powershell
cd backend
pytest
```

### Frontend Tests
```powershell
cd frontend
npm test
```

## Development Scripts

### Backend
- `scripts/start-local.ps1` - PowerShell script to start local backend

### Frontend
- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run unit tests

## Database Migrations

The project uses Alembic for database migrations:

```powershell
cd backend
# Create new migration
alembic revision --autogenerate -m "Migration message"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use production-grade secrets management
2. **Firebase Credentials**: Store securely, not in repository
3. **Database**: Use managed PostgreSQL service
4. **Redis**: Use managed Redis service
5. **SSL/TLS**: Enable HTTPS
6. **Container Registry**: Push images to registry for deployment

### Docker Production Build

```powershell
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Frontend Not Accessible
- Ensure Angular dev server is binding to all interfaces: `ng serve --host 0.0.0.0`
- Check firewall/antivirus blocking port 4200
- Verify container is running: `docker-compose ps`

### Backend Environment Errors
- Ensure `backend/.env` exists and all required variables are set
- Check database connectivity
- Verify Firebase credentials file exists and path is correct

### Database Connection Issues
- Ensure PostgreSQL is running and accessible
- Wait for database to be ready before running migrations
- Check connection string in `.env`

### WebSocket Connection Failed
- Verify Redis is running and accessible
- Check WebSocket URL in frontend environment
- Ensure backend WebSocket endpoint is running

### Firebase Authentication Issues
- Verify Firebase project configuration
- Ensure service account JSON file is valid and accessible
- Check Firebase project ID matches in both backend and frontend

### Docker Compose Issues
- Ensure Docker and Docker Compose are installed
- Check for port conflicts (4200, 8000, 5432, 6379)
- Rebuild images if changes don't take effect: `docker-compose up -d --build`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest` (backend) and `npm test` (frontend)
5. Commit changes: `git commit -am 'Add your feature'`
6. Push to branch: `git push origin feature/your-feature`
7. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the robust backend framework
- Angular for the frontend framework
- Firebase for authentication
- PostgreSQL and Redis for data persistence and caching

