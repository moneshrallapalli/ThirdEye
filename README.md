# 🛡️ AI-Powered Video Intelligence Platform

An intelligent video-intelligence platform that analyses live camera feeds with **Anthropic Claude** for vision and reasoning, uses **Google Gemini** for a natural-language command center, and builds semantic context with **ChromaDB**. It ships with JWT authentication, email alerts, and a real-time React dashboard.

## 🌟 Features

### Core Capabilities
- **🤖 Vision Agent**: Real-time frame analysis using Claude (Sonnet 4) — object detection, scene description, significance scoring
- **🧠 Reasoning Agent**: Claude (Haiku 4.5) decides when an observation warrants an alert and explains why
- **💬 AI Command Center**: Natural-language control powered by Google Gemini — describe what to watch for and it fans the task out to every live camera
- **🔎 Context Agent**: Semantic search and pattern recognition over past events with ChromaDB vector embeddings
- **📊 Real-time Dashboard**: Live feeds, alerts, scene narration, and statistics over WebSockets
- **🔐 Authentication**: Email/password signup with JWT and email verification
- **📧 Email Alerts**: Themed alert + verification emails via Resend
- **🚨 Anomaly Detection**: Identifies unusual patterns versus normal behaviour

### 💬 AI Command Center
Control your surveillance system using natural language. Type what you want:
- "Watch for people entering the building"
- "Alert me if you see any vehicles"
- "Monitor for suspicious activity"

The system parses your intent, confirms what it will do, persists the task, and runs it in real time across all live cameras. Commands are listed under `GET /api/ai-commands` and can be cancelled.

### Technology Stack

**Backend:**
- FastAPI with WebSocket support
- Anthropic Claude (vision + reasoning agents)
- Google Gemini (AI command center)
- ChromaDB for vector embeddings / semantic search
- PostgreSQL (SQLAlchemy) for event, camera, alert, and user storage
- Redis (provisioned via Docker for caching/scale-out)
- OpenCV for video capture and processing
- Resend for transactional email

**Frontend:**
- React 18 with TypeScript
- Tailwind CSS for styling
- React Router for navigation and auth-gated pages
- Chart.js + Recharts for data visualization
- Real-time WebSocket communication

## 🚀 Quick Start

### One-Command Start (Recommended)

**Linux/Mac:**
```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env and set (at minimum):
#   CLAUDE_API_KEY=...      # required — vision + reasoning
#   GEMINI_API_KEY=...      # required — AI command center
#   POSTGRES_PASSWORD=...   # required
#   SECRET_KEY=...          # required — JWT signing

# 2. Start everything
./start.sh

# Dashboard opens automatically at http://localhost:3000
```

**Windows:**
```batch
REM 1. Configure environment
copy backend\.env.example backend\.env
REM Edit backend\.env and set CLAUDE_API_KEY, GEMINI_API_KEY, POSTGRES_PASSWORD, SECRET_KEY

REM 2. Start everything
start.bat

REM Dashboard opens automatically at http://localhost:3000
```

**Stop the system:**
```bash
./stop.sh       # Linux/Mac
stop.bat        # Windows
```

See [QUICK_START.md](QUICK_START.md) and [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup, [API_KEY_SETUP.md](API_KEY_SETUP.md) for obtaining the Claude/Gemini keys, and [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md) for the auth/email flow.

### Docker Start

```bash
# 1. Configure environment (see above)
cp backend/.env.example backend/.env

# 2. Start with Docker
./start-docker.sh        # or: docker-compose up -d

# View logs
docker-compose logs -f

# Stop
./stop-docker.sh         # or: docker-compose down
```

`docker-compose` brings up PostgreSQL, Redis, the FastAPI backend, and the React frontend.

### What the Start Script Does
- ✅ Checks prerequisites (Python, Node.js, databases)
- ✅ Creates the Python virtual environment (first run)
- ✅ Installs backend and frontend dependencies
- ✅ Initializes the database (first run)
- ✅ Starts PostgreSQL (and Redis when available)
- ✅ Starts the backend server (port 8000)
- ✅ Starts the frontend server (port 3000)
- ✅ Opens the dashboard in your browser

## 🔧 Configuration

### Backend (`backend/.env`)
```env
# AI Providers (both required)
CLAUDE_API_KEY=your_anthropic_api_key   # vision + reasoning agents
GEMINI_API_KEY=your_gemini_api_key       # AI command center
GOOGLE_PROJECT_ID=your_google_project_id # optional

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sentintinel_db
POSTGRES_USER=sentintinel_user
POSTGRES_PASSWORD=secure_password        # required

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chromadb_data

# Security (required)
SECRET_KEY=change-me-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Email (Resend — verification + alert mail)
RESEND_API_KEY=your_resend_api_key
RESEND_FROM=ThirdEye <onboarding@resend.dev>
EMAIL_RECIPIENT=alerts@example.com
FRONTEND_URL=http://localhost:3000
APP_PUBLIC_URL=http://localhost:3000

# Camera Settings
CAMERA_FPS=1.0                 # one fresh frame per second (Claude calls are throttled on top)
MAX_CAMERAS=4
VIDEO_RESOLUTION_WIDTH=640
VIDEO_RESOLUTION_HEIGHT=480
ANALYSIS_MIN_INTERVAL_SECONDS=3.0

# Localisation — IANA tz used in emails/logs (empty = server local time)
DISPLAY_TIMEZONE=

# Alert Thresholds
CRITICAL_THRESHOLD=80
WARNING_THRESHOLD=50
IMMEDIATE_ALERT_THRESHOLD=60
ACTIVITY_DETECTION_THRESHOLD=40
```

### Frontend (`frontend/.env`)
```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000
```

## 📖 Usage Guide

> Most `/api` endpoints require authentication. Sign up / log in first and send the
> returned token as `Authorization: Bearer <token>`.

### Authentication
```bash
# Sign up (triggers a verification email)
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password"}'

# Log in to get a JWT
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password"}'
```

### Adding Cameras
```bash
curl -X POST http://localhost:8000/api/cameras \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Front Entrance",
    "location": "Building A - Main Door",
    "stream_url": "rtsp://camera-url",
    "tasks": [{"command": "Alert me if a vehicle stops", "task_type": "custom"}]
  }'
```

### Starting / Stopping Camera Analysis
```bash
curl -X POST http://localhost:8000/api/cameras/1/start -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/cameras/1/stop  -H "Authorization: Bearer <token>"
```

### Querying a Camera (natural language)
```bash
curl -X POST http://localhost:8000/api/cameras/1/query \
  -H "Content-Type: application/json" -H "Authorization: Bearer <token>" \
  -d '{"question": "Is anyone at the door right now?"}'
```

### Viewing Alerts
```bash
curl http://localhost:8000/api/alerts -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/alerts?severity=CRITICAL" -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/alerts/1/acknowledge -H "Authorization: Bearer <token>"
```

## 🏗️ Architecture

### System Components
```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐           │
│  │Live Feeds│  │  Alerts  │  │ Command Center│          │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘           │
│       └─────────────┼───────────────┘                    │
│                     │ REST + WebSocket                    │
└─────────────────────┼───────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────┐
│              FastAPI Backend                             │
│  ┌──────────────────┴───────────────────┐               │
│  │   Auth (JWT)  │   WebSocket Manager   │               │
│  └──────────────────┬───────────────────┘               │
│   ┌──────────────┬──┴───────────┬───────────────┐       │
│   │ Vision Agent │ Reasoning    │ Command Agent  │       │
│   │ (Claude)     │ Agent(Claude)│ (Gemini)       │       │
│   └──────┬───────┴──────┬───────┴───────┬────────┘       │
│          │              │               │                │
│  ┌───────┴──────┐ ┌─────┴──────┐ ┌─────┴────────┐       │
│  │   Camera     │ │ PostgreSQL │ │  ChromaDB     │       │
│  │   Service    │ │ (events)   │ │  (vectors)    │       │
│  └──────────────┘ └────────────┘ └───────────────┘       │
└──────────────────────────────────────────────────────────┘
```

### Data Flow
1. **Video Capture**: Camera Service captures frames (~1 FPS by default).
2. **Vision Analysis**: Vision Agent sends frames to Claude for object/scene analysis.
3. **Reasoning**: Reasoning Agent (Claude) scores significance and decides on alerts.
4. **Context Building**: Context Agent stores scene embeddings in ChromaDB.
5. **Event Storage**: Events, detections, and alerts are persisted in PostgreSQL.
6. **Notification**: Critical alerts trigger Resend emails; the dashboard updates over WebSocket.

## 🎯 Key Features Explained

### Vision Agent (Claude)
- Analyses video frames and extracts object detections and scene descriptions
- Calculates significance scores used downstream for alerting

### Reasoning Agent (Claude)
- Reviews the vision output and decides whether an alert is warranted, with reasoning
- Aligns alert severity to configurable thresholds

### Command Agent (Gemini)
- Parses natural-language commands into surveillance tasks
- Fans tasks out across live cameras; tasks are persisted and cancellable

### Context Agent (ChromaDB)
- **Semantic Search**: Find similar past events using vector embeddings
- **Temporal Context**: What happened before/after an event
- **Anomaly Detection**: Identify unusual patterns
- **Object Tracking**: Track appearances over time

### Alert System
- **Severity Levels**: CRITICAL, WARNING, INFO, SYSTEM
- **Priority-based Routing**: Critical alerts trigger immediate email notifications
- **Response Tracking**: Acknowledge alerts individually or in bulk
- **Context-aware**: Alerts include reasoning and an evidence frame

## 🔌 API Endpoints

### Auth
- `POST /api/auth/signup` — Create account (sends verification email)
- `POST /api/auth/login` — Obtain JWT
- `GET /api/auth/me` — Current user
- `GET /api/auth/verify-email` — Verify email via token
- `POST /api/auth/resend-verification` — Resend verification email

### Cameras
- `GET /api/cameras` — List cameras
- `POST /api/cameras` — Create camera (with optional tasks)
- `DELETE /api/cameras/{id}` — Delete camera
- `POST /api/cameras/{id}/start` — Start analysis
- `POST /api/cameras/{id}/stop` — Stop analysis
- `POST /api/cameras/{id}/query` — Ask a question about the live feed
- `POST /api/cameras/{id}/history` — Question-aligned history lookup
- `GET|POST|PUT|DELETE /api/cameras/{id}/tasks` — Manage per-camera tasks

### AI Commands
- `GET /api/ai-commands` — List active commands
- `DELETE /api/ai-commands` — Cancel/clear commands

### Events, Alerts & Search
- `GET /api/events` — Events (with filters)
- `GET /api/alerts` — Alerts (with filters)
- `GET /api/alerts/recent-events` — Recent alert activity
- `POST /api/alerts/{id}/acknowledge` — Acknowledge an alert
- `POST /api/alerts/acknowledge-all` — Acknowledge all
- `DELETE /api/alerts` / `DELETE /api/alerts/{id}` — Clear alerts
- `POST /api/search/scenes` — Semantic scene search
- `POST /api/video/query-scene` · `POST /api/video/timeline` · `GET /api/video/capabilities`
- `GET /api/frames/list` · `GET /api/frames/recent` · `DELETE /api/frames/{filename}`

### Stats, Patterns & System
- `GET /api/stats/summary` — Summary statistics
- `GET /api/patterns` — Identified patterns
- `GET /api/system/health` — Health check
- `POST /api/system/command` — System command
- `GET /api/camera-presets` — Built-in camera presets
- `POST /api/email/test-alert` — Send a test alert email

## 🔌 WebSocket Endpoints
- `/ws/live-feed` — Live video feed updates
- `/ws/alerts` — Real-time alert notifications
- `/ws/analysis` — Scene analysis/narration stream
- `/ws/system` — System messages and commands

## 🛠️ Development

### Running Tests
```bash
cd backend && pytest        # backend tests (incl. email/camera test scripts)
cd frontend && npm test     # frontend tests
```

### Linting / Formatting
```bash
# Backend
flake8 backend/
black backend/

# Frontend
cd frontend && npm run lint
```

## 🔒 Security Considerations
1. **API Keys**: Never commit `.env` files (already in `.gitignore`).
2. **JWT Secret**: Set a strong `SECRET_KEY` in production.
3. **HTTPS**: Use HTTPS in production.
4. **Authentication**: All data endpoints require a valid Bearer token.
5. **Rate Limiting**: Consider rate limiting public endpoints.

## 🐛 Troubleshooting

### Backend won't boot
- Ensure `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, and `SECRET_KEY` are set — these are required and have no defaults.

### Camera won't start
- Check the stream URL is reachable and OpenCV can read the source; review logs.

### WebSocket disconnections
- Check CORS settings, the WebSocket URL, and network connectivity.

### Claude / Gemini API errors
- Verify the relevant key is valid and within quota; review API response logs.

### Database connection issues
- Verify PostgreSQL is running, credentials in `.env` are correct, and the database exists.

## 📝 License
MIT License

## 🤝 Contributing
Contributions welcome — please open an issue or PR.

---

**AI-Powered Video Intelligence Platform — built with Anthropic Claude, Google Gemini, ChromaDB, and FastAPI.**
