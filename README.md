# ORCA — Marine EcOsystem Reasoning with Collaborative Agents
### Smart India Hackathon (SIH) — Production-Style Maritime Intelligence Prototype

[![Backend Regression Tests](https://img.shields.io/badge/Backend%20Tests-98%20Passed-brightgreen)](backend/tests/)
[![Frontend Build](https://img.shields.io/badge/Frontend-Vite%20TypeScript-blue)](frontend/)
[![Frontend Lint](https://img.shields.io/badge/Frontend%20Lint-0%20Warnings%20%2F%200%20Errors-brightgreen)](frontend/)
[![Architecture](https://img.shields.io/badge/Architecture-LangGraph%20%2B%20FastAPI%20%2B%20React-blueviolet)](backend/app/workflows/orca_graph.py)
[![Data Provenance](https://img.shields.io/badge/Provenance-Live%20Open--Meteo%20%2B%20Official%20INCOIS%20Snapshot-orange)](backend/app/tools/)

ORCA is an agentic AI-powered conversational marine intelligence platform engineered for coastal fishers, safety authorities, and vessel operators in the **Kochi, Kerala (Arabian Sea)** maritime sector. It integrates live atmospheric and oceanographic APIs, official historical INCOIS advisory data, and deterministic navigational mathematics within a multi-agent orchestration architecture.

---

## 🏛️ System Architecture

ORCA employs a 6-agent collaborative collective orchestrated with **LangGraph**:

```text
                                  User Query
                                      │
                                      ▼
                        FastAPI Gateway (POST /api/chat)
                                      │
                                      ▼
                ┌───────────────────────────────────────────┐
                │        LangGraph Agent Orchestrator       │
                │                                           │
                │   ┌───────────────────────────────────┐   │
                │   │           PlannerAgent            │   │
                │   │  (Intent, Entity, Ref, Context)   │   │
                │   └─────────────────┬─────────────────┘   │
                │                     │                     │
                │       ┌─────────────┼─────────────┐       │
                │       ▼             ▼             ▼       │
                │  WeatherAgent   OceanAgent  GeospatialAgent│
                │  (Open-Meteo)  (Open-Meteo) (INCOIS/GIS)  │
                │       └─────────────┬─────────────┘       │
                │                     │                     │
                │                     ▼                     │
                │             RiskAssessmentAgent           │
                │     (Vessel Limits, 4-Factor Route Risk)  │
                │                     │                     │
                │                     ▼                     │
                │               EvidenceAgent               │
                │       (Audit Trail & Provenance Ledger)   │
                └─────────────────────┬─────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
    Deterministic Engines                           Persistence & Delivery
  - SafeRoutingEngine (3 Alternatives)            - SQLite StorageRepository
  - Haversine / Bearing Math                      - ConversationStore (Rehydration)
  - Ray-Casting Geofencing                        - Deterministic AlertEngine
  - Cross-Track Error Detection                   - React / Vite / Leaflet UI
```

### Agent Roles

| Agent | Responsibility | Data Source / Engine |
| :--- | :--- | :--- |
| **PlannerAgent** | Resolves multi-turn referents, extracts locations/coordinates/destinations, identifies craft profile, detects temporal windows | `context_resolver.py`, SQLite session |
| **WeatherAgent** | Retrieves 10-meter wind speed, gust, precipitation probability, weather codes, and temperature | Live Open-Meteo Weather API (`weather_data.py`) |
| **OceanAgent** | Retrieves wave height, direction, swell period, currents, sea temperature, and tidal trend | Live Open-Meteo Marine API (`ocean_data.py`) |
| **GeospatialAgent** | Calculates Great Circle distances, bearings, radial filters, candidate comparisons, and polygon geofences | Historical INCOIS PFZ snapshot (`pfz_data.py`), GIS polygons (`gis_data.py`) |
| **RiskAssessmentAgent** | Evaluates composite safety scores, vessel seaworthiness limits, and 4-factor Route Risk Index (0–10) | Central config (`risk_thresholds.py`), `route_risk.py` |
| **EvidenceAgent** | Formulates transparent provenance claims, bilingual outputs (English / Malayalam), and limitations | `evidence.py`, `llm_service.py` |

---

## 📊 Data Pipeline & Provenance Truth Table

ORCA adheres strictly to **zero data hallucination**:

| Parameter / Layer | Source / Adapter | Mode | Authenticity & Limitations |
| :--- | :--- | :--- | :--- |
| **Wind Speed & Rain** | Open-Meteo Weather API v1 | **LIVE** | Live HTTP request with verified `retrieved_at` machine timestamp. Cached for 15 min. |
| **Wave Height & Swell** | Open-Meteo Marine API v1 | **LIVE** | Live offshore grid evaluation. Direction and period modeled from ECMWF/GFS marine physics. |
| **PFZ Target Advisories** | ESSO-INCOIS Kerala Snapshot | **HISTORICAL** | Official advisory snapshot dated `2024-03-08` associated with coastal landing centres. Never described as real-time. |
| **Restricted Maritime Zones** | Demo GIS GeoJSON Layers | **DEMO** | Kochi Naval Base Security Perimeter and Vypin Dredging Channel polygons. |
| **Passage Routing & Clearances**| `SafeRoutingEngine` | **CALCULATED** | Deterministic waypoint generation, 1.5 km polygon clearance buffer, 3 route alternatives. |
| **Route Risk Index (0–10)** | `assess_prototype_route_risk` | **CALCULATED** | Deterministic 4-factor composite: Environmental (35%), Vessel stress (25%), Distance (20%), Geofence (20%). |
| **Chlorophyll-a / Ocean Color** | `EarthObservationAdapter` | **UNAVAILABLE** | Intentionally marked `UNAVAILABLE` when unconfigured. Never mocked or fabricated. |
| **Lightning Risk & Live AIS** | Open-Meteo / None | **UNAVAILABLE** | Explicitly reported as unsupported/unavailable rather than inferred. |

---

## 🖥️ Four Specialized Workspaces

The frontend provides four distinct, dedicated dashboards:

1. **💬 ORCA Chat (`/chat`)**:
   - Natural conversational interface with auto-scrolling feed, quick query suggestions, and bilingual response generation (English & Malayalam).
   - In-line telemetry metrics, risk cards, and candidate target cards.
2. **🗺️ Marine Intelligence (`/marine`)**:
   - Full Leaflet maritime map displaying INCOIS PFZ targets, restricted naval boundaries, and vessel reference stations.
   - Interactive layer toggles, radius filters (15 km, 25 km, 30 km, 50 km), and route alternatives overlay.
3. **🚤 Route & Safety (`/route`)**:
   - Passage planning workspace featuring **3 Route Alternatives**:
     - *Direct Route (Baseline)*: Minimum distance, intersects restricted security zones.
     - *Safe Passage Corridor (Avoidance)*: 1.5 km geometric clearance buffer, 100% boundary clearance.
     - *High-Clearance Seaward Corridor*: 4.0 km seaward margin for heavy weather.
   - 4-Factor Prototype Route Risk Index (0–10) with limiting factor identification.
   - Clean empty state when no active route exists.
4. **📊 Data & Evidence (`/evidence`)**:
   - Complete audit trail of all agent execution steps (`agent_trace`).
   - Source provenance metadata inspector with retrieval timestamps, fallback status, and limitation notices.

---

## ⚡ Deterministic Maritime Alert Engine

ORCA evaluates real-time maritime hazards deterministically without LLM speculation:
- **Restricted Zone Proximity Alert**: Triggers `CRITICAL` violation when inside a restricted polygon, or `WARNING` when within the 2.0 km safety buffer.
- **Craft Threshold Alert**: Compares live wave height and wind speed against active vessel profile limits (`traditional_craft`, `motorized_frp_obm`, `mechanized_trawler`, or custom).
- **Route Deviation / Cross-Track Alert**: Computes perpendicular distance from vessel to active route corridor; triggers `WARNING` when cross-track error exceeds 1.0 km.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ and npm
- Git

### 1. Backend Setup

```bash
# Navigate to repository root
cd ORCA-Marine-Intelligence

# Activate virtual environment (Windows)
backend\.venv\Scripts\activate
# Or on Unix: source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run FastAPI server
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

FastAPI server runs at: `http://127.0.0.1:8000`  
API Interactive Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup

```bash
# In a separate terminal
cd frontend

# Install npm dependencies
npm install

# Run Vite dev server
npm run dev
```

Frontend application runs at: `http://localhost:5173`

---

## 🧪 Verification & Test Suite

The project features a **100% passing test suite with 98 automated regression and integration tests**:

```bash
# Run complete test suite (from repo root)
backend\.venv\Scripts\python.exe -m pytest backend/tests -v

# Run frontend build and linter
cd frontend
npm run build
npm run lint
```

### Test Coverage Highlights

| Test Module | Tests | Verifies |
| :--- | :---: | :--- |
| `test_api.py` | 4 | REST endpoints (`/health`, `/spatial/layers`, `/chat`) |
| `test_conversation_context.py` | 9 | Multi-turn memory, pronoun referents, session isolation |
| `test_gis.py` | 5 | Great-circle Haversine, bearing, ray-casting geofencing |
| `test_live_adapters.py` | 16 | Open-Meteo Weather/Marine parsing, caching, fallbacks |
| `test_m5_advanced_reasoning.py` | 7 | Destination routing, 3 alternatives, sampling limitation |
| `test_m5_integration.py` | 7 | Temporal comparison, radial filtering, candidate comparison |
| `test_m6_data_expansion.py` | 4 | Unified `DataSourceAdapter`, provenance metadata, unconfigured EO |
| `test_m7_product_integration.py` | 8 | SQLite storage, rehydration, alert engine, REST CRUD |
| `test_pfz_candidates.py` | 5 | Candidate ranking, Haversine filtering, paired comparisons |
| `test_pfz_snapshot.py` | 11 | Historical INCOIS snapshot schema, provenance, fallbacks |
| `test_risk.py` | 4 | Rule-based risk engine, composite thresholds |
| `test_route_risk.py` | 4 | 4-factor Route Risk Index calculation and stress ratios |
| `test_temporal_reasoning.py` | 5 | Window comparisons, tolerance classification (IMPROVING/WORSENING) |
| `test_vessel_routing.py` | 7 | Craft seaworthiness parameters, geofence avoidance |
| `test_workflow.py` | 3 | Full LangGraph state machine execution end-to-end |
| **Total** | **98** | **All Passing (0 Failures, 0 Regressions)** |

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/chat` | `POST` | Core multi-agent conversational reasoning endpoint |
| `/api/spatial/layers` | `GET` | Returns GeoJSON FeatureCollections for PFZ and restricted zones |
| `/api/conversations` | `GET` | Lists recent conversation sessions with turn counts and context |
| `/api/conversations/{id}` | `GET` | Returns stored context and full message history for a session |
| `/api/conversations/{id}` | `DELETE` | Deletes a conversation session, history, and associated alerts |
| `/api/vessel-profiles` | `GET` | Lists all available vessel seaworthiness profiles |
| `/api/vessel-profiles` | `POST` | Creates or updates a custom craft seaworthiness profile |
| `/api/alerts` | `GET` | Lists active maritime alerts (filter by `conversation_id`) |
| `/api/alerts/evaluate` | `POST` | Manually triggers deterministic proximity/threshold/route alert check |
| `/api/health` | `GET` | System readiness and operational mode check |

---

## 🛡️ Disclaimers

1. **Prototype Decision Support**: ORCA is a research and demonstration prototype developed for Smart India Hackathon (SIH). It is not an official statutory navigation system, SOLAS replacement, or certified seaworthiness authority.
2. **Historical PFZ Data**: PFZ targets are derived from official ESSO-INCOIS historical advisories. Target proximity does not guarantee present-day biological suitability or fish catch.
3. **Route Planning**: Safe Passage Corridors provide geometric avoidance around configured zones based on calm-water assumptions; mariners must exercise continuous bridge watchkeeping and observe COLREGs.
