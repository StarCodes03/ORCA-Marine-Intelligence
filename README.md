# ORCA — Marine Ecosystem Reasoning with Collaborative Agents
### SIH 2026 Prototype — Milestone 1

ORCA is an Agentic AI-powered conversational marine intelligence platform designed to deliver coastal safety advisories, Potential Fishing Zone (PFZ) insights, and hydrodynamic situational awareness for artisanal and mechanized fishers.

For **Milestone 1**, the application implements the core architecture, LangGraph multi-agent orchestration, deterministic geospatial calculations, transparent rule-based risk engines, and interactive Leaflet map dashboard focused on the **Kochi, Kerala (Arabian Sea)** coastal sector using clearly marked mock data adapters.

---

## Architecture Overview

```
User Query
    ↓
FastAPI Backend (POST /api/chat)
    ↓
LangGraph Orchestrator (orca_graph.py)
    ↓
PlannerAgent (Intent, Entity & Agent Decomposition)
    ↓
Conditional Routing
    ├── WeatherAgent (MOCK_WEATHER_DATA adapter)
    ├── OceanAgent (MOCK_OCEAN_DATA adapter)
    └── GeospatialAgent (DEMO_GIS_DATA: Haversine & Geofencing)
    ↓
RiskAssessmentAgent (Rule-based evaluation via config/risk_thresholds.py)
    ↓
Evidence & Synthesis Agent (Audit trail & transparent explanation)
    ↓
React + Vite + Leaflet Interactive Dashboard
```

### Key Technical Attributes
1. **Deterministic Calculations**: Great Circle distances to PFZs and point-in-polygon geofencing checks for restricted security zones are calculated mathematically (Haversine & Jordan curve ray-casting), never guessed by an LLM.
2. **Transparent Rule-Based Risk Engine**: Centralized safety thresholds defined in `backend/app/config/risk_thresholds.py`. No arbitrary AI hallucination of safety hazards.
3. **Mock Data Adapters**: Sensor telemetry and satellite layers are isolated behind clean adapter services (`weather_data.py`, `ocean_data.py`, `gis_data.py`), ready to connect to live INCOIS/IMD/Copernicus APIs in future milestones.
4. **Offline / Mock Mode by Default**: Runs out of the box with zero external API key requirements. When `GEMINI_API_KEY` or `OPENAI_API_KEY` is provided in `.env`, the LLM service layer can leverage model capabilities.
5. **Full Execution Audit Trace**: Every agent execution step is recorded in `agent_trace` and viewable in the frontend developer inspection drawer.

---

## Directory Structure

```
ORCA-Marine-Intelligence/
├── README.md
├── .env.example
├── .env
├── data/
│   └── demo/
│       ├── pfz.geojson                  # Demo PFZs off Kochi (Chellanam, Vypin, Munambam)
│       └── restricted_zones.geojson     # Demo naval & port exclusion polygons
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                      # FastAPI entry point & CORS
│   │   ├── api/
│   │   │   └── routes.py                # /api/chat, /api/health, /api/spatial/layers
│   │   ├── agents/
│   │   │   ├── planner.py               # PlannerAgent
│   │   │   ├── weather.py               # WeatherAgent
│   │   │   ├── ocean.py                 # OceanAgent
│   │   │   ├── geospatial.py            # GeospatialAgent
│   │   │   ├── risk.py                  # RiskAssessmentAgent
│   │   │   └── evidence.py              # EvidenceAgent
│   │   ├── config/
│   │   │   └── risk_thresholds.py       # Central marine safety threshold rules
│   │   ├── models/
│   │   │   └── schemas.py               # Pydantic data schemas
│   │   ├── services/
│   │   │   └── llm_service.py           # LLM service abstraction with deterministic fallback
│   │   ├── tools/
│   │   │   ├── weather_data.py          # MOCK_WEATHER_DATA adapter
│   │   │   ├── ocean_data.py            # MOCK_OCEAN_DATA adapter
│   │   │   └── gis_data.py              # DEMO_GIS_DATA adapter & GIS math
│   │   └── workflows/
│   │       └── orca_graph.py            # LangGraph multi-agent state graph
│   └── tests/                           # 14 Pytest unit & integration tests
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── src/
    │   ├── App.tsx                      # Main split-view dashboard
    │   ├── components/
    │   │   ├── Header.tsx               # Status & sector banner
    │   │   ├── ChatPanel.tsx            # Conversational console & telemetry cards
    │   │   └── AgentTraceDrawer.tsx     # Developer trace & payload inspector
    │   ├── map/
    │   │   └── MarineMap.tsx            # Leaflet map with PFZ & restricted zone layers
    │   └── services/
    │       └── api.ts                   # Backend API client
```

---

## Getting Started

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ and npm

---

### 1. Backend Setup & Execution

1. Open a terminal in the project root:
   ```bash
   cd ORCA-Marine-Intelligence
   ```

2. Create and activate a Python virtual environment:
   **Windows (PowerShell):**
   ```powershell
   python -m venv backend/.venv
   backend/.venv/Scripts/Activate.ps1
   ```
   **Linux / macOS:**
   ```bash
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. Run the automated test suite to verify all agents and GIS algorithms:
   ```bash
   python -m pytest backend/tests -v
   ```

5. Start the FastAPI backend server:
   **Windows (PowerShell):**
   ```powershell
   backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
   ```
   The backend API will be live at: `http://127.0.0.1:8000`  
   API Documentation: `http://127.0.0.1:8000/docs`  
   Health Check: `http://127.0.0.1:8000/api/health`

---

### 2. Frontend Setup & Execution

1. Open a new terminal in the `frontend` folder:
   ```bash
   cd ORCA-Marine-Intelligence/frontend
   ```

2. Install npm dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend dashboard will be available at: `http://localhost:5173`

---

## Acceptance Test Queries

In the chat interface, you can click the quick-prompt buttons or type:

### Query 1: Marine Safety
> *"Is it safe to go fishing near Kochi tomorrow morning?"*

- **Intent**: `marine_safety`
- **Location**: Kochi (9.9312° N, 76.2673° E)
- **Agents Executed**: `PlannerAgent` ➔ `WeatherAgent` ➔ `OceanAgent` ➔ `GeospatialAgent` ➔ `RiskAssessmentAgent` ➔ `EvidenceAgent`
- **Assessed Risk**: **HIGH RISK** (Wind: 32 km/h, Waves: 1.8 m, Moderate Lightning)
- **Map Action**: Displays Kochi vessel and nearby maritime safety buffer.

### Query 2: Potential Fishing Zone (PFZ) Search
> *"Where is the nearest potential fishing zone?"*

- **Intent**: `pfz_search`
- **Agents Executed**: `PlannerAgent` ➔ `OceanAgent` ➔ `GeospatialAgent` ➔ `EvidenceAgent` (*Weather and Risk agents are conditionally bypassed*)
- **Nearest PFZ**: Chellanam Offshore PFZ (~23 km SW, Bearing ~222°, SST 28.2°C, Chlorophyll 0.85 mg/m³)
- **Map Action**: Zooms to target PFZ and draws a dashed navigation vector line from vessel to PFZ.

### Query 3: Marine Meteorology & Ocean State
> *"What are the tide, weather and sea conditions near my fishing location?"*

- **Intent**: Comprehensive marine conditions
- **Displays**: Structured cards for Wind, Rain, Lightning, Wave Height, Sea State, and Tide.

---

## Milestone 1 Verification Status

- [x] LangGraph state graph with conditional routing
- [x] Isolated mock adapters (`MOCK_WEATHER_DATA`, `MOCK_OCEAN_DATA`, `DEMO_GIS_DATA`)
- [x] Mathematical Haversine & ray-casting geofencing
- [x] Centralized configurable risk thresholds in `config/risk_thresholds.py`
- [x] FastAPI `/api/chat`, `/api/health`, `/api/spatial/layers`
- [x] Leaflet map displaying Kochi, PFZ points, and restricted zones
- [x] Collapsible Developer Audit Trace drawer
- [x] 14 passing automated tests (`test_gis.py`, `test_risk.py`, `test_workflow.py`, `test_api.py`)
