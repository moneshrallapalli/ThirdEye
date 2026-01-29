# 🛡️ ThirdEye - AI-Powered Surveillance System

An intelligent surveillance system powered by Google Gemini Live API with real-time video analysis, semantic context building using ChromaDB, and advanced pattern recognition.

## 🌟 Features

### Core Capabilities
- **🤖 AI Vision Agent**: Real-time video analysis using Gemini Live API
- **💬 AI Command Center**: Natural language interface for surveillance control - **NEW!**
- **🧠 Context Agent**: Semantic search and pattern recognition with ChromaDB
- **📊 Real-time Dashboard**: Live feeds, alerts, and scene narration
- **🔍 Anomaly Detection**: Identifies unusual patterns vs normal behavior
- **📝 Historical Context**: Track object appearances over time
- **⚡ WebSocket Integration**: Real-time updates for all components

### 🆕 AI Command Center (NEW!)
Control your surveillance system using natural language! Simply type what you want:
- "Watch for people entering the building"
- "Alert me if you see any vehicles"
- "Monitor for suspicious activity"

The system understands your intent, confirms what it will do, and executes tasks in real-time. See [AI_COMMAND_USAGE.md](AI_COMMAND_USAGE.md) for detailed guide.

### Technology Stack

**Backend:**
- FastAPI with WebSocket support
- PostgreSQL for event storage
- ChromaDB for vector embeddings
- Redis for caching
- Google Gemini Live API
- OpenCV for video processing

**Frontend:**
- React 18 with TypeScript
- Tailwind CSS for styling
- Real-time WebSocket communication
- Recharts for data visualization

## 🚀 Quick Start

### One-Command Start (Recommended)

**Linux/Mac:**
```bash
# 1. Add your Gemini API key to backend/.env
cp backend/.env.example backend/.env
# Edit backend/.env and add GEMINI_API_KEY=your_key_here

# 2. Start everything
./start.sh

# Dashboard opens automatically at http://localhost:3000
```

**Windows:**
```batch
REM 1. Add your Gemini API key to backend\.env
copy backend\.env.example backend\.env
REM Edit backend\.env and add GEMINI_API_KEY=your_key_here

REM 2. Start everything
start.bat

REM Dashboard opens automatically at http://localhost:3000
```

**Stop the system:**
```bash
./stop.sh       # Linux/Mac
stop.bat        # Windows
```

### Docker Start (Also Easy)

```bash
# 1. Add your Gemini API key
cp backend/.env.example backend/.env
# Edit backend/.env and add GEMINI_API_KEY=your_key_here

# 2. Start with Docker
./start-docker.sh

# Stop with Docker
./stop-docker.sh
```

### What the Start Script Does
- ✅ Checks all prerequisites (Python, Node.js, databases)
- ✅ Creates virtual environment (first run)
- ✅ Installs dependencies automatically
- ✅ Initializes database (first run)
- ✅ Starts PostgreSQL and Redis
- ✅ Starts backend server (port 8000)
- ✅ Starts frontend server (port 3000)
- ✅ Opens dashboard in your browser

**See [QUICK_START.md](QUICK_START.md) for detailed instructions**

## 📦 Docker Setup (Recommended)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🔧 Configuration

### Backend (.env)
```env
# API Configuration
GEMINI_API_KEY=your_api_key_here

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sentintinel_db
POSTGRES_USER=sentintinel_user
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chromadb_data

# Camera Settings
CAMERA_FPS=2
MAX_CAMERAS=4
VIDEO_RESOLUTION_WIDTH=1280
VIDEO_RESOLUTION_HEIGHT=720

# Alert Thresholds
CRITICAL_THRESHOLD=80
WARNING_THRESHOLD=50
```

### Frontend (.env)
```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000
```

## 📖 Usage Guide

### Adding Cameras

**Via API:**
```bash
curl -X POST http://localhost:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Front Entrance",
    "location": "Building A - Main Door",
    "stream_url": "rtsp://camera-url"
  }'
```

**Via Dashboard:**
1. Navigate to the dashboard
2. Add camera configuration
3. Click "Start" to begin streaming

### Starting Camera Analysis

```bash
# Start camera 1
curl -X POST http://localhost:8000/api/cameras/1/start

# Stop camera 1
curl -X POST http://localhost:8000/api/cameras/1/stop
```

### Viewing Alerts

**Via API:**
```bash
# Get all alerts
curl http://localhost:8000/api/alerts

# Get critical alerts only
curl http://localhost:8000/api/alerts?severity=CRITICAL

# Acknowledge alert
curl -X POST http://localhost:8000/api/alerts/1/acknowledge
```

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │Live Feeds│  │  Alerts  │  │ Analysis │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       └─────────────┼─────────────┘                     │
│                     │ WebSocket                          │
└─────────────────────┼─────────────────────────────────┘
                      │
┌─────────────────────┼─────────────────────────────────┐
│              FastAPI Backend                           │
│  ┌─────────────────┴──────────────────┐               │
│  │      WebSocket Manager              │               │
│  └─────────────────┬──────────────────┘               │
│                    │                                    │
│  ┌────────────────┼────────────────┐                  │
│  │  Vision Agent  │  Context Agent  │                  │
│  │  (Gemini API) │  (ChromaDB)    │                  │
│  └────────────────┴────────────────┘                  │
│         │                 │                             │
│  ┌──────┴─────┐   ┌──────┴──────┐                    │
│  │  Camera    │   │  PostgreSQL  │                    │
│  │  Service   │   │  Database    │                    │
│  └────────────┘   └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Video Capture**: Camera Service captures frames at 2 FPS
2. **Analysis**: Vision Agent sends frames to Gemini for analysis
3. **Context Building**: Context Agent stores embeddings in ChromaDB
4. **Pattern Recognition**: Similar events queried for context
5. **Event Storage**: Events and detections stored in PostgreSQL
6. **Real-time Updates**: WebSocket broadcasts to connected clients

## 🎯 Key Features Explained

### Vision Agent
- Analyzes video frames using Gemini Live API
- Extracts object detections, scene descriptions
- Calculates significance scores
- Generates alerts based on thresholds

### Context Agent
- **Semantic Search**: Find similar past events using vector embeddings
- **Temporal Context**: What happened before/after an event
- **Anomaly Detection**: Identify unusual patterns
- **Object Tracking**: Track appearances over time
- **Pattern Recognition**: Identify daily routines, regular visitors

### Alert System
- **4 Severity Levels**: CRITICAL, WARNING, INFO, SYSTEM
- **Priority-based Routing**: Critical alerts trigger immediate notifications
- **Response Tracking**: Measure acknowledgment times
- **Context-aware**: Alerts include historical context

## 🔌 API Endpoints

### Cameras
- `GET /api/cameras` - List all cameras
- `POST /api/cameras` - Create camera
- `POST /api/cameras/{id}/start` - Start camera
- `POST /api/cameras/{id}/stop` - Stop camera

### Events
- `GET /api/events` - Get events (with filters)

### Alerts
- `GET /api/alerts` - Get alerts (with filters)
- `POST /api/alerts/{id}/acknowledge` - Acknowledge alert

### Statistics
- `GET /api/stats/summary` - Get summary statistics

### Patterns
- `GET /api/patterns` - Get identified patterns

### System
- `GET /api/system/health` - Health check

## 🔌 WebSocket Endpoints

- `/ws/live-feed` - Live video feed updates
- `/ws/alerts` - Real-time alert notifications
- `/ws/analysis` - Scene analysis/narration stream
- `/ws/system` - System messages and commands

## 🛠️ Development

### Running Tests
```bash
cd backend
pytest

cd frontend
npm test
```

### Database Migrations
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Linting
```bash
# Backend
flake8 backend/
black backend/

# Frontend
npm run lint
```

## 📊 Monitoring

### System Health
```bash
curl http://localhost:8000/api/system/health
```

### WebSocket Connections
Check the dashboard for active connection statistics

### Database Statistics
View ChromaDB stats in the Summary panel

## 🔒 Security Considerations

1. **API Keys**: Never commit `.env` files
2. **Authentication**: Implement authentication for production
3. **HTTPS**: Use HTTPS in production
4. **Input Validation**: All inputs are validated
5. **Rate Limiting**: Implement rate limiting for APIs

## 🐛 Troubleshooting

### Camera won't start
- Check stream URL is accessible
- Verify OpenCV can read the source
- Check logs for errors

### WebSocket disconnections
- Check CORS settings
- Verify WebSocket URL
- Check network connectivity

### Gemini API errors
- Verify API key is valid
- Check quota limits
- Review API response logs

### Database connection issues
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure database exists

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📧 Support

For issues and questions, please open a GitHub issue.

---

**Built with ❤️ using Google Gemini Live API, ChromaDB, and FastAPI**
