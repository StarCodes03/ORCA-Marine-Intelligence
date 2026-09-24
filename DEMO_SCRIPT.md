# ORCA — Live Demonstration Script (5–7 Minutes)
### Smart India Hackathon (SIH) Evaluation Guide

This curated walkthrough guides evaluators and judges through the core agentic capabilities, deterministic reasoning engines, and user-facing dashboards of **ORCA (Marine Ecosystem Reasoning with Collaborative Agents)**.

---

## ⏱️ Demonstration Timeline Summary

```text
┌─────────────────┬──────────────────────────────────────────┬─────────────────┐
│ Time            │ Demonstration Act                        │ Primary Screen  │
├─────────────────┼──────────────────────────────────────────┼─────────────────┤
│ 00:00 – 00:45   │ 1. Architecture & Live Ingestion Setup   │ /chat + Header  │
│ 00:45 – 02:00   │ 2. Craft-Aware Safety & Bilingual Output │ /chat           │
│ 02:00 – 03:00   │ 3. Multi-Turn Temporal Trend Analysis    │ /chat           │
│ 03:00 – 04:30   │ 4. Safe Corridor & 3 Route Alternatives  │ /route          │
│ 04:30 – 05:45   │ 5. PFZ Candidate Reasoning & GIS Map     │ /marine         │
│ 05:45 – 07:00   │ 6. Alerts Engine & Evidence Ledger       │ /evidence       │
└─────────────────┴──────────────────────────────────────────┴─────────────────┘
```

---

## 🧭 Canonical 8-Step Judge Evaluation Flow

For rapid benchmarking and live presentation scoring, follow this verified 8-step sequence against a fresh session:

| Step | Action / Query | Workspace | Key Verification Checks |
| :---: | :--- | :---: | :--- |
| **1** | `"Is it safe to go fishing near Kochi tomorrow morning?"` | 💬 `/chat` | Environmental condition risk level & score, key marine factors, prototype origin caution, nearest historical INCOIS PFZ, concise passage summary, no data dump. |
| **2** | `"What about afternoon?"` | 💬 `/chat` | Context retained without repeating "Kochi". Deterministic morning vs afternoon delta comparison (wind, waves, sea state trend). |
| **3** | `"Show PFZ targets within 30 km."` | 💬 `/chat` | Historical INCOIS snapshot terminology. Top 3–5 candidate targets in compact table with distance/bearing, total target count, and Marine Map action. |
| **4** | `"Which one is closest?"` | 💬 `/chat` | Resolves target #1 (Kuzhuppilly / Chellanam), explicit snapshot distance and bearing from harbor, explicit historical advisory status. |
| **5** | `"Is there a restricted zone between me and that target?"` | 💬 `/chat` | Deterministic ray-casting intersection against Cochin Naval Base perimeter. Wording avoids legal/regulatory claims. Suggests viewing Route & Safety. |
| **6** | Open **Marine Intelligence** | 🗺️ `/marine` | Leaflet map displays historical PFZ markers, restricted naval zones, harbor origin, and route corridor. Radial distance filters responsive. |
| **7** | Open **Route & Safety** | 🚤 `/route` | Active vessel profile, 3 route alternatives (Direct vs Safe Corridor vs Seaward), clearance buffer avoidance, 4-Factor Route Risk Index, prototype disclaimer. |
| **8** | Open **Data & Evidence** | 📊 `/evidence` | Weather = `LIVE`, Marine = `LIVE`, PFZ = `OFFICIAL SNAPSHOT`, Lightning = `UNSUPPORTED`, Chlorophyll = `UNAVAILABLE`, full agent execution audit trace. |

---

## Act 1: System Introduction & Live Ingestion Setup (00:00 – 00:45)

### Goal
Demonstrate that ORCA is not a chatbot hallucinating answers, but a multi-agent collective connecting live meteorological feeds with deterministic safety engines.

1. **Open the Application**: Open `http://localhost:5173` in a web browser.
2. **Examine the Application Shell**:
   - Point out the persistent left sidebar with the four core workspaces:
     - 💬 **ORCA Chat**
     - 🗺️ **Marine Intelligence**
     - 🚤 **Route & Safety**
     - 📊 **Data & Evidence**
   - Point out the top header showing **Sector: Kochi, Kerala (Arabian Sea)** and **Source Status: READY** (clean initial state awaiting query).

---

## Act 2: Craft-Aware Coastal Safety Assessment (00:45 – 02:00)

### Goal
Show how ORCA differentiates risk based on specific vessel seaworthiness limits rather than generic weather summaries.

1. In the **ORCA Chat** input box, select **Motorized FRP Canoe (OBM)** from the vessel selector.
2. Type or click:
   ```text
   Can I go fishing off Kochi this morning?
   ```
3. **Key Points to Highlight for Judges**:
   - **Agent Execution**: Watch the badge indicating LangGraph agent orchestration (`PlannerAgent` ➔ `WeatherAgent` ➔ `OceanAgent` ➔ `RiskAssessmentAgent` ➔ `EvidenceAgent`).
   - **Live Ingestion**: Open-Meteo returns live wind speed and wave height for Kochi's exact coordinates (9.9312°N, 76.2673°E).
   - **Vessel Awareness**: The composite risk score specifically evaluates the FRP Canoe's safe wave ceiling (1.6 m) and wind limit (30 km/h).
   - **Bilingual Output**: Show the synthesized response in both English and clear, maritime-accurate **Malayalam** (തീരദേശ സുരക്ഷാ അറിയിപ്പ്).

---

## Act 3: Multi-Turn Temporal Trend Analysis (02:00 – 03:00)

### Goal
Demonstrate conversational context retention without re-prompting location or vessel type.

1. In the same chat session, enter:
   ```text
   What about afternoon?
   ```
2. **Key Points to Highlight for Judges**:
   - **Context Resolution**: Notice the user did *not* repeat "Kochi" or "FRP Canoe". The `PlannerAgent` extracted the `afternoon` time modifier and preserved the session state from SQLite.
   - **Deterministic Comparison**: ORCA compares morning vs afternoon conditions using mathematical tolerance boundaries (wave delta ±0.15 m, wind delta ±3.0 km/h).
   - **Trend Classification**: Explicit status reported as **IMPROVING**, **WORSENING**, or **STABLE**, with actionable guidance on the safest operational window.

---

## Act 4: Destination Routing & 3 Route Alternatives (03:00 – 04:30)

### Goal
Showcase destination-aware passage planning, geometric obstacle avoidance, and the 4-factor Route Risk Index.

1. In the chat, enter:
   ```text
   Calculate a safe route from Kochi to Munambam for my vessel
   ```
2. Wait for the response, then click **🚤 Route & Safety** in the left sidebar (or click the route link in chat).
3. **Key Points to Highlight for Judges**:
   - **3 Route Alternatives**:
     - *Direct Route (Baseline)*: Shortest distance, but cuts through the Kochi Naval Base Security Perimeter (`INTERSECTS ZONE`).
     - *Safe Passage Corridor (Recommended)*: Applies a deterministic 1.5 km polygon clearance buffer around the naval boundary. 100% collision-free.
     - *High-Clearance Seaward Corridor*: 4.0 km seaward margin for adverse weather avoidance.
   - **Prototype Route Risk Index (0–10)**: Explain the 4-factor breakdown:
     - Environmental conditions (35%)
     - Vessel stress ratios (25%)
     - Route distance exposure (20%)
     - Geofence safety clearance (20%)
   - **Sampling Notice**: Show the explicit disclaimer acknowledging that environmental conditions are sampled at discrete waypoints rather than continuous hydrodynamic integration.

---

## Act 5: PFZ Candidate Reasoning & Spatial Domain (04:30 – 05:45)

### Goal
Demonstrate official INCOIS snapshot filtering, Haversine candidate ranking, and pairwise target comparison without hallucinating fish abundance.

1. In chat or switch to **🗺️ Marine Intelligence**:
   ```text
   Show PFZ targets within 30 km of Kochi
   ```
2. Follow up with:
   ```text
   Compare target 1 and target 2
   ```
3. **Key Points to Highlight for Judges**:
   - **Haversine Distance**: All candidate distances and bearings are calculated deterministically from Kochi Harbor reference station.
   - **INCOIS Snapshot Authenticity**: Targets come from the official INCOIS Kerala snapshot (dated 2024-03-08) associated with coastal landing centres.
   - **Honest Transparency**: The comparison table explicitly lists *unavailable fields* (real-time chlorophyll-a, live fish abundance, SST satellite passes) rather than fabricating numbers.
   - **Interactive Layer Controls**: Toggle PFZ markers, restricted zones, and route alternative polylines on the Leaflet map.

---

## Act 6: Alert Engine & Data Evidence Ledger (05:45 – 07:00)

### Goal
Demonstrate the deterministic maritime alert engine, real machine timestamps, and the complete audit trail.

1. Click on **📊 Data & Evidence** in the left sidebar.
2. **Key Points to Highlight for Judges**:
   - **Source Provenance Table**:
     - Atmospheric Weather: `Open-Meteo Weather API v1` (Shows exact machine `retrieved_at` timestamp).
     - Oceanographic: `Open-Meteo Marine API v1` (Live offshore wave model).
     - PFZ / GIS: `ESSO-INCOIS Advisory Archive` (Explicitly marked `OFFICIAL SNAPSHOT`).
     - Chlorophyll / Ocean Color: Explicitly marked `UNAVAILABLE` (zero hallucination).
   - **Agent Execution Trace**: Click on individual agents (`PlannerAgent`, `GeospatialAgent`, `RiskAssessmentAgent`) in the trace inspector to inspect their exact input and output payloads.
   - **Local Alert Engine**:
     - Proximity alerts (triggers inside naval perimeter or within 2.0 km).
     - Seaworthiness threshold alerts (wave/wind exceedance).
     - Route deviation alert (cross-track error > 1.0 km).

---

## 🎯 Wrap-Up Elevator Pitch for Judges

> "ORCA bridges the gap between complex satellite/oceanographic data and coastal fishers on the water. By orchestrating collaborative agents with deterministic navigation math and zero-hallucination provenance, ORCA delivers life-saving safety advisories and fuel-efficient passage planning that mariners can truly trust."
