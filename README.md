# SponsorPulse 🚀

**Autonomous Industry & Corporate Engagement Outreach Engine**

SponsorPulse is a production-grade local outreach management platform designed for the Industry & Corporate Engagement Program — placing students/graduates, managing campus hiring partnerships, and establishing sponsored training sessions with recently funded companies.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React Frontend (Vite :5173)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Discovery     │  │ Kanban Board │  │ Email Draft      │   │
│  │ Panel         │  │ (DnD)        │  │ Modal            │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ /api (proxy)
┌────────────────────────▼────────────────────────────────────┐
│  FastAPI Backend (:8000)                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ Discovery│ │Enrichment│ │ Outreach │ │ Gmail Auth   │   │
│  │ Routes   │ │ Routes   │ │ Routes   │ │ Routes       │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘   │
│       │             │            │               │           │
│  ┌────▼──┐ ┌───────▼───┐ ┌─────▼────┐ ┌───────▼────────┐  │
│  │Scraper│ │Enricho MCP│ │Gemini API│ │Gmail OAuth+API │  │
│  │Service│ │ Client    │ │ Service  │ │ Service        │  │
│  └───────┘ └───────────┘ └──────────┘ └────────────────┘  │
│                                                             │
│  SQLite (SQLAlchemy ORM + Alembic)                         │
└─────────────────────────────────────────────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| **Funding Discovery** | Automated RSS scraping from TechCrunch & VentureBeat, with regex-based extraction of company names, funding amounts, and rounds |
| **Contact Enrichment** | MCP JSON-RPC 2.0 integration with Enricho.co to find decision-makers (VPs, CTOs, HR leads) |
| **AI Email Generation** | Google Gemini 2.0 Flash-powered cold pitch generation tailored for corporate engagement partnerships |
| **Gmail Integration** | Desktop OAuth (RFC 8252) for sending emails and tracking thread replies directly from the pipeline |
| **Kanban Pipeline** | Drag-and-drop board tracking companies from Discovery → Enriched → Drafted → Ready → Sent → Replied |
| **Safety Controls** | Human-in-the-loop review modal with domain safety warnings before sending |

## Pipeline Stages

```
DISCOVERED → ENRICHED → DRAFTED → READY_TO_SEND → SENT → REPLIED → CLOSED
```

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** with npm
- Google Cloud Project with Gmail API enabled (for email features)
- Enricho.co API key (for contact enrichment)
- Google Gemini API key (for AI email generation)

### 1. Clone & Configure

```bash
cd sponsorpulse
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run Both Servers

```bash
# Terminal 1 — Backend (from backend/)
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend (from frontend/)
npm run dev
```

Or use the automated script:

```bash
# Windows
.\run_local.bat

# macOS/Linux
chmod +x run_local.sh && ./run_local.sh
```

### 5. Open the App

Navigate to **http://localhost:5173** in your browser.

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key for AI email generation | ✅ |
| `ENRICHO_API_KEY` | Enricho.co API key for contact enrichment | ✅ |
| `ENRICHO_MCP_SERVER_URL` | Enricho MCP endpoint URL | ✅ |
| `DATABASE_URL` | SQLite connection string | Default: `sqlite:///./sponsorpulse.db` |
| `CORS_ORIGINS` | Allowed CORS origins JSON array | Default: `["http://localhost:5173"]` |

### Gmail OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Gmail API**
3. Create OAuth 2.0 credentials → **Desktop Application**
4. Download `credentials.json` to `backend/credentials/`
5. Click "Connect Gmail" in the SponsorPulse UI to authenticate

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/discovery/sync` | Trigger RSS feed sync |
| `GET` | `/api/discovery/companies` | List discovered companies |
| `GET` | `/api/discovery/companies/:id` | Get company details |
| `POST` | `/api/enrichment/enrich/:id` | Enrich company contacts via MCP |
| `GET` | `/api/enrichment/contacts/:id` | List company contacts |
| `GET` | `/api/enrichment/mcp-status` | Check MCP connection status |
| `GET` | `/api/kanban/board` | Get full Kanban board state |
| `PUT` | `/api/kanban/move/:id` | Move card to new stage |
| `GET` | `/api/kanban/stats` | Pipeline statistics |
| `POST` | `/api/outreach/generate-email/:id` | Generate AI email draft |
| `PUT` | `/api/outreach/draft/:id` | Edit email draft |
| `POST` | `/api/outreach/approve/:id` | Approve draft for sending |
| `POST` | `/api/outreach/send/:id` | Send email via Gmail |
| `POST` | `/api/outreach/sync-replies` | Check for thread replies |
| `GET` | `/api/auth/google/status` | Gmail auth status |
| `GET` | `/api/auth/google/url` | Get OAuth URL |
| `GET` | `/api/auth/google/callback` | OAuth callback handler |

---

## Project Structure

```
sponsorpulse/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI route handlers
│   │   │   ├── discovery.py     # RSS feed sync & company listing
│   │   │   ├── enrichment.py    # MCP contact enrichment
│   │   │   ├── outreach.py      # Email generation, sending, replies
│   │   │   ├── kanban.py        # Board state & card movement
│   │   │   └── auth_gmail.py    # Google OAuth flow
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings from .env
│   │   │   └── database.py      # SQLAlchemy engine & session
│   │   ├── models/
│   │   │   └── models.py        # Company, Contact, Outreach ORM
│   │   ├── services/
│   │   │   ├── scraper_service.py      # RSS feed parser
│   │   │   ├── mcp_enricho_service.py  # MCP JSON-RPC 2.0 client
│   │   │   ├── gemini_service.py       # Gemini AI email generator
│   │   │   └── gmail_service.py        # Gmail OAuth & send/track
│   │   └── main.py              # FastAPI app entry point
│   ├── credentials/             # OAuth credentials (gitignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DiscoveryPanel.tsx      # Funding feed browser
│   │   │   ├── KanbanBoard.tsx         # Drag-and-drop pipeline
│   │   │   ├── KanbanCard.tsx          # Individual pipeline card
│   │   │   ├── EmailDraftModal.tsx     # Email review/edit modal
│   │   │   └── GmailAuthButton.tsx     # OAuth connect button
│   │   ├── services/api.ts            # Axios API client
│   │   ├── types/index.ts             # TypeScript interfaces
│   │   ├── App.tsx                     # Main application layout
│   │   └── main.tsx                    # React entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
└── README.md
```

---

## License

Private — Internal use for Industry & Corporate Engagement Program.

