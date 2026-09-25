/**
 * ORCA Marine Intelligence - Centralized Role Configuration
 * 
 * Defines the 9 specialized personas for the shared ORCA platform.
 * Personalizes dashboard layout, priority information, suggested questions,
 * terminology, map emphasis, and default workflows without creating
 * separate applications, separate datasets, or fake telemetry.
 */

export type RoleId =
  | 'fisherman'
  | 'vessel_operator'
  | 'port_authority'
  | 'search_and_rescue'
  | 'marine_researcher'
  | 'fisheries_officer'
  | 'environmental_officer'
  | 'tourism_operator'
  | 'general_user';

export interface DashboardSectionConfig {
  id: string;
  title: string;
  description: string;
  priority: number;
}

export interface MapEmphasisConfig {
  showPfz: boolean;
  showRestricted: boolean;
  showRoute: boolean;
  showVessel: boolean;
  highlightFocus: 'pfz' | 'route' | 'restricted' | 'general' | 'environmental';
  badgeText: string;
}

export interface RoleTerminologyConfig {
  riskAssessmentLabel?: string;
  routeLabel?: string;
  landingCenterLabel?: string;
  roleDisclaimer?: string;
  actionCallout?: string;
}

export interface RoleConfig {
  id: RoleId;
  displayName: string;
  shortName: string;
  icon: string;
  purpose: string;
  tagline: string;
  defaultTab: '/chat' | '/marine' | '/route' | '/evidence';
  defaultVessel: string;
  priorities: string[];
  suggestedQuestions: string[];
  dashboardSections: DashboardSectionConfig[];
  mapEmphasis: MapEmphasisConfig;
  terminology: RoleTerminologyConfig;
}

export const ROLES_CONFIG: Record<RoleId, RoleConfig> = {
  fisherman: {
    id: 'fisherman',
    displayName: 'Fisherman',
    shortName: 'Fisherman',
    icon: '🎣',
    purpose: 'Help fishermen make practical fishing and safety decisions.',
    tagline: 'Fishing safety, PFZs & safe operational windows',
    defaultTab: '/chat',
    defaultVessel: 'motorized_frp_obm',
    priorities: [
      'Fishing safety & seaworthiness',
      'Weather & atmospheric conditions',
      'Wave height & sea state',
      'Safe fishing windows (morning vs afternoon)',
      'Potential Fishing Zone (PFZ) discovery',
      'Distance & bearing to nearest PFZ',
      'Restricted-zone warnings & perimeters',
      'Safe passage route to fishing area'
    ],
    suggestedQuestions: [
      'Is it safe to go fishing today?',
      'When is the better fishing window today?',
      'Show nearby PFZs.',
      'Show PFZs within 30 km.',
      'What are the sea conditions today?',
      'Is tomorrow morning suitable for fishing?'
    ],
    dashboardSections: [
      { id: 'fishing_conditions', title: "Today's Fishing Conditions", description: 'Live wave, wind, and sea conditions for coastal fishing crafts.', priority: 1 },
      { id: 'safe_window', title: 'Safe Fishing Window', description: 'Deterministic morning vs afternoon seaworthiness comparison.', priority: 2 },
      { id: 'nearby_pfzs', title: 'Nearby PFZs', description: 'Official INCOIS Potential Fishing Zones with distances and bearings.', priority: 3 },
      { id: 'sea_conditions', title: 'Sea Conditions', description: 'Significant wave height, sea state, and tidal movement trend.', priority: 4 },
      { id: 'restricted_zones', title: 'Restricted Zones', description: 'Configured naval and port channel perimeters to avoid during transit.', priority: 5 },
      { id: 'route_to_pfz', title: 'Route to PFZ', description: '1.5 km buffer corridor avoiding configured security perimeters.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: true,
      showRestricted: true,
      showRoute: true,
      showVessel: true,
      highlightFocus: 'pfz',
      badgeText: 'PFZ & Restricted Zone Clearance'
    },
    terminology: {
      riskAssessmentLabel: 'FISHING CRAFT SAFETY ADVISORY',
      routeLabel: 'FISHING TRANSIT PASSAGE',
      landingCenterLabel: 'Landing Centre / Harbour',
      roleDisclaimer: 'Advisory decision-support for artisanal and small-craft fishers. Not a legal navigation authority.',
      actionCallout: 'Check safe fishing windows and verify geofence clearance before departure.'
    }
  },

  vessel_operator: {
    id: 'vessel_operator',
    displayName: 'Boat / Vessel Operator',
    shortName: 'Vessel Operator',
    icon: '🚤',
    purpose: 'Support vessel navigation and operational passage planning.',
    tagline: 'Routes, vessel limits, fuel estimates & clearance corridors',
    defaultTab: '/route',
    defaultVessel: 'mechanized_trawler',
    priorities: [
      'Vessel seaworthiness & category limits',
      'Route safety & hazard clearance',
      'Weather & marine conditions',
      'Wave conditions & sea state',
      'Restricted maritime perimeters',
      'Safe passage corridors (1.5 km margin)',
      'Vessel operating parameters',
      'Transit distance & estimated duration',
      'Fuel consumption estimates'
    ],
    suggestedQuestions: [
      'Is this route safe?',
      'Show a safe passage corridor.',
      'Are there restricted zones on this route?',
      'What are the current wave conditions?',
      'How long will this route take?'
    ],
    dashboardSections: [
      { id: 'vessel_safety', title: 'Vessel Safety & Limits', description: 'Seaworthiness profile, engine limits, and wave thresholds.', priority: 1 },
      { id: 'route_safety', title: 'Route & Safety Analysis', description: 'Direct vs corridor passage evaluation with distance and duration.', priority: 2 },
      { id: 'weather_ocean', title: 'Weather & Ocean Conditions', description: 'Forecast atmospheric wind, wave height, and swell observations.', priority: 3 },
      { id: 'restricted_zones', title: 'Restricted Security Zones', description: 'Configured naval base buffer and port traffic security perimeters.', priority: 4 },
      { id: 'passage_corridor', title: 'Passage Corridor Plan', description: 'Waypoints diverted around restricted zones with 1.5 km margin.', priority: 5 },
      { id: 'fuel_duration', title: 'Fuel / Distance / Duration', description: 'Speed-based transit hours and estimated fuel burn for craft category.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: true,
      showRestricted: true,
      showRoute: true,
      showVessel: true,
      highlightFocus: 'route',
      badgeText: 'Safe Passage Corridor & Waypoints'
    },
    terminology: {
      riskAssessmentLabel: 'VESSEL SEAWORTHINESS & TRANSIT RISK',
      routeLabel: 'NAVIGATION CORRIDOR',
      landingCenterLabel: 'Departure Port / Harbour',
      roleDisclaimer: 'Decision-support passage planning for vessel masters. Not for official ECDIS or live vessel autopilot navigation.',
      actionCallout: 'Review vessel thresholds and restricted-zone clearance before casting off.'
    }
  },

  port_authority: {
    id: 'port_authority',
    displayName: 'Coastal / Port Authority',
    shortName: 'Port Authority',
    icon: '🏛️',
    purpose: 'Provide marine situational awareness for coastal and port operations.',
    tagline: 'Situational awareness, maritime boundaries & risk conditions',
    defaultTab: '/marine',
    defaultVessel: 'mechanized_trawler',
    priorities: [
      'Marine operational risk assessment',
      'Weather and ocean swell observations',
      'Restricted maritime perimeters & channels',
      'Vessel transit routes & corridors',
      'Operational coastal hazards',
      'Geographic maritime situation'
    ],
    suggestedQuestions: [
      'What are the current marine risk conditions?',
      'Show restricted maritime zones.',
      'Which areas require caution?',
      'What are today\'s coastal conditions?',
      'Show current safe passage corridors.'
    ],
    dashboardSections: [
      { id: 'situation_overview', title: 'Marine Situation Overview', description: 'Coastal sector conditions and geographic situational picture.', priority: 1 },
      { id: 'risk_assessment', title: 'Marine Risk Assessment', description: 'Composite environmental risk index across wind, waves, and sea state.', priority: 2 },
      { id: 'restricted_zones', title: 'Restricted Maritime Zones', description: 'Configured security boundaries including Naval Base and Port Channel.', priority: 3 },
      { id: 'weather_ocean', title: 'Weather & Ocean Conditions', description: 'Verified Open-Meteo live atmospheric and hydrodynamic feeds.', priority: 4 },
      { id: 'route_safety', title: 'Route Safety & Corridors', description: 'Corridors and geometric buffer zones evaluated for passage.', priority: 5 },
      { id: 'evidence_sources', title: 'Evidence & Data Sources', description: 'Provenance trace and audit trail for upstream data feeds.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: false,
      showRestricted: true,
      showRoute: true,
      showVessel: true,
      highlightFocus: 'restricted',
      badgeText: 'Restricted Boundaries & Operational Corridors'
    },
    terminology: {
      riskAssessmentLabel: 'COASTAL OPERATIONAL HAZARD INDEX',
      routeLabel: 'MONITORED TRANSIT CORRIDOR',
      landingCenterLabel: 'Port Authority Sector / Terminal',
      roleDisclaimer: 'Informational decision support for port area awareness. Does NOT access official government port radar, naval systems, classified data, or live AIS vessel tracking.',
      actionCallout: 'Monitor environmental thresholds and configured security buffer zones.'
    }
  },

  search_and_rescue: {
    id: 'search_and_rescue',
    displayName: 'Search & Rescue / Emergency',
    shortName: 'Search & Rescue',
    icon: '🛟',
    purpose: 'Provide environmental and route intelligence that could assist emergency-response planning.',
    tagline: 'Environmental risk, adverse marine conditions & hazard avoidance',
    defaultTab: '/marine',
    defaultVessel: 'motorized_frp_obm',
    priorities: [
      'Current weather & wind velocities',
      'Significant wave height & swell conditions',
      'Sea state & wave conditions',
      'Restricted zones & navigation barriers',
      'Route conditions & corridor clearance',
      'Composite environmental risk index',
      'Geographic situational context'
    ],
    suggestedQuestions: [
      'What are the current sea conditions?',
      'Which route has fewer configured hazards?',
      'What are the current wave and wind conditions?',
      'Show restricted zones.',
      'What are the environmental conditions around Kochi?'
    ],
    dashboardSections: [
      { id: 'current_conditions', title: 'Current Marine Conditions', description: 'Rapid-scan forecast conditions for wind, precipitation, and sea swell.', priority: 1 },
      { id: 'environmental_risk', title: 'Environmental Risk Evaluation', description: 'Hazard index highlighting adverse sea states and wind thresholds.', priority: 2 },
      { id: 'route_safety', title: 'Route & Hazard Clearance', description: 'Corridor analysis indicating geometry clear of security zones.', priority: 3 },
      { id: 'restricted_zones', title: 'Restricted Zones & Hazards', description: 'Configured security perimeters to consider during movement.', priority: 4 },
      { id: 'marine_map', title: 'Marine Sector Map', description: 'Geographic visualization of coastal sector and waypoints.', priority: 5 },
      { id: 'data_evidence', title: 'Data & Evidence Provenance', description: 'Source endpoints and retrieval timestamps for verified planning inputs.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: false,
      showRestricted: true,
      showRoute: true,
      showVessel: true,
      highlightFocus: 'environmental',
      badgeText: 'Hazard Awareness & Environmental Conditions'
    },
    terminology: {
      riskAssessmentLabel: 'EMERGENCY ENVIRONMENTAL RISK INDEX',
      routeLabel: 'RESPONSE PASSAGE CORRIDOR',
      landingCenterLabel: 'Response Staging Harbour',
      roleDisclaimer: 'Prototype environmental intelligence only. Does NOT provide live 911/emergency dispatch, real-time vessel tracking, or official Coast Guard SAR coordination.',
      actionCallout: 'Assess environmental hazards and sea state before deploying resources.'
    }
  },

  marine_researcher: {
    id: 'marine_researcher',
    displayName: 'Marine Researcher / Oceanographer',
    shortName: 'Researcher',
    icon: '🌊',
    purpose: 'Explore marine environmental data, forecast trends, and data provenance.',
    tagline: 'Oceanographic observations, temporal forecast comparison & provenance audit',
    defaultTab: '/evidence',
    defaultVessel: 'mechanized_trawler',
    priorities: [
      'Oceanographic observations & marine conditions',
      'Atmospheric weather & pressure trends',
      'Significant wave height & period',
      'Sea-level & tidal trend harmonics',
      'Sea surface temperature (SST) observations',
      'Historical INCOIS PFZ spatial data',
      'Temporal comparisons (morning vs afternoon)',
      'Data source provenance & audit trail'
    ],
    suggestedQuestions: [
      'Compare today\'s morning and afternoon conditions.',
      'What is the current wave height?',
      'How is the sea-level trend changing?',
      'Show PFZ data.',
      'What environmental data is available?'
    ],
    dashboardSections: [
      { id: 'ocean_conditions', title: 'Oceanographic Hydrodynamics', description: 'Significant wave height, direction, swell period, and sea surface temperature.', priority: 1 },
      { id: 'weather_telemetry', title: 'Atmospheric Weather Observations', description: 'Wind speed, atmospheric temperature, and precipitation probabilities.', priority: 2 },
      { id: 'temporal_comparison', title: 'Temporal Trend Comparison', description: 'Calculated metric deltas between forecasting windows.', priority: 3 },
      { id: 'pfz_data', title: 'INCOIS PFZ Dataset', description: 'Historical spatial coordinates and sector bearings from landing centres.', priority: 4 },
      { id: 'environmental_indicators', title: 'Environmental Indicators', description: 'Verified parameters: SST, tidal harmonics, sea state scale.', priority: 5 },
      { id: 'provenance_audit', title: 'Data Provenance & Audit Trail', description: 'Complete pipeline trace with API endpoints and retrieval timestamps.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: true,
      showRestricted: true,
      showRoute: false,
      showVessel: true,
      highlightFocus: 'environmental',
      badgeText: 'Ocean Observations & INCOIS Coordinates'
    },
    terminology: {
      riskAssessmentLabel: 'ENVIRONMENTAL HYDRODYNAMIC METRICS',
      routeLabel: 'OBSERVATIONAL TRANSECT',
      landingCenterLabel: 'Sampling / Reference Landing Point',
      roleDisclaimer: 'Scientific observation exploration. Uses Open-Meteo forecast APIs and historical INCOIS snapshots. Unsupported parameters (e.g. Chlorophyll-a) are transparently labeled.',
      actionCallout: 'Analyze forecast deltas and inspect retrieval timestamps in Data & Evidence.'
    }
  },

  fisheries_officer: {
    id: 'fisheries_officer',
    displayName: 'Fisheries Officer',
    shortName: 'Fisheries Officer',
    icon: '🐟',
    purpose: 'Support fisheries-related situational awareness and fishing-zone analysis.',
    tagline: 'PFZ zone analysis, seasonal windows & landing context',
    defaultTab: '/marine',
    defaultVessel: 'motorized_frp_obm',
    priorities: [
      'Potential Fishing Zone (PFZ) intelligence',
      'Fishing activity context & vessel profiles',
      'Marine conditions across landing sectors',
      'Safe fishing windows (morning vs afternoon)',
      'Coastal marine conditions near harbours',
      'Historical INCOIS PFZ spatial data',
      'Spatial distance & bearing information'
    ],
    suggestedQuestions: [
      'Show PFZ targets near Kochi.',
      'Compare available PFZ targets.',
      'What are today\'s marine conditions?',
      'Which PFZ is closest?',
      'Compare today\'s marine conditions with tomorrow.'
    ],
    dashboardSections: [
      { id: 'pfz_overview', title: 'PFZ Target Overview', description: 'Landing-centre referenced fishing zone coordinates and descriptions.', priority: 1 },
      { id: 'marine_conditions', title: 'Marine Conditions in Sector', description: 'Wave height, swell, and wind conditions across Kochi fishing waters.', priority: 2 },
      { id: 'fishing_windows', title: 'Morning vs Afternoon Fishing Windows', description: 'Morning vs afternoon sea state trends for small-scale fleet.', priority: 3 },
      { id: 'pfz_map', title: 'PFZ Spatial Distribution', description: 'Interactive visual distribution of historical INCOIS targets.', priority: 4 },
      { id: 'distance_bearing', title: 'Distance & Bearing Analysis', description: 'Geodesic nautical distance from major landing centres (Chellanam, Munambam, Vypin).', priority: 5 },
      { id: 'data_provenance', title: 'Data Provenance & Source Info', description: 'Official INCOIS snapshot metadata and Open-Meteo weather verification.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: true,
      showRestricted: true,
      showRoute: true,
      showVessel: true,
      highlightFocus: 'pfz',
      badgeText: 'PFZ Distribution & Landing Centres'
    },
    terminology: {
      riskAssessmentLabel: 'FISHERIES SECTOR RISK EVALUATION',
      routeLabel: 'FISHING TRANSIT CORRIDOR',
      landingCenterLabel: 'Designated Coastal Landing Centre',
      roleDisclaimer: 'Fisheries situational decision-support. Does NOT access live department databases or proprietary vessel registry systems.',
      actionCallout: 'Inspect PFZ distribution and verify advisory sea state for the artisanal fleet.'
    }
  },

  environmental_officer: {
    id: 'environmental_officer',
    displayName: 'Marine Conservation / Environmental Officer',
    shortName: 'Environmental Officer',
    icon: '🌱',
    purpose: 'Support environmental monitoring and coastal marine-area awareness.',
    tagline: 'Coastal awareness, restricted areas & verified indicators',
    defaultTab: '/evidence',
    defaultVessel: 'traditional_craft',
    priorities: [
      'Ocean hydrodynamic conditions',
      'Verified environmental indicators actually available',
      'Restricted marine perimeters & enclaves',
      'Spatial coastal context & habitat proximity',
      'PFZ and environmental data relationship',
      'Strict data provenance and sensor limits'
    ],
    suggestedQuestions: [
      'What are the current ocean conditions?',
      'Show restricted marine areas.',
      'What environmental indicators are available?',
      'Compare today\'s ocean conditions.',
      'Show PFZ/environmental data.'
    ],
    dashboardSections: [
      { id: 'ocean_conditions', title: 'Ocean Conditions & Swell', description: 'Wave dynamics, significant wave height, and sea state.', priority: 1 },
      { id: 'environmental_indicators', title: 'Available Environmental Indicators', description: 'Transparently verified indicators: SST, tide harmonics, sea state scale.', priority: 2 },
      { id: 'marine_map', title: 'Coastal Environmental Map', description: 'Spatial layout of coastal enclaves, ports, and landing centres.', priority: 3 },
      { id: 'restricted_zones', title: 'Restricted Marine Perimeters', description: 'Configured security geometries and navigational buffer boundaries.', priority: 4 },
      { id: 'temporal_trends', title: 'Temporal Environmental Trends', description: 'Day-to-day and morning-to-afternoon metric fluctuations.', priority: 5 },
      { id: 'evidence_sources', title: 'Evidence & Sources Audit', description: 'Verified upstream sources (Open-Meteo & INCOIS snapshot) with provenance stamps.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: true,
      showRestricted: true,
      showRoute: false,
      showVessel: true,
      highlightFocus: 'restricted',
      badgeText: 'Restricted Enclaves & Environmental Observations'
    },
    terminology: {
      riskAssessmentLabel: 'ENVIRONMENTAL SWELL & WEATHER INDEX',
      routeLabel: 'MONITORED TRANSIT PATH',
      landingCenterLabel: 'Coastal Ecosystem Sector',
      roleDisclaimer: 'Honest environmental decision support. Does NOT invent pollution levels, biodiversity observations, species counts, or chlorophyll measurements.',
      actionCallout: 'Review verified upstream indicators and restricted area geometries.'
    }
  },

  tourism_operator: {
    id: 'tourism_operator',
    displayName: 'Coastal / Maritime Tourism Operator',
    shortName: 'Tourism Operator',
    icon: '🧭',
    purpose: 'Help tourism operators understand marine conditions relevant to coastal activities.',
    tagline: 'Coastal boat trips, wave conditions & sea safety forecasts',
    defaultTab: '/marine',
    defaultVessel: 'motorized_frp_obm',
    priorities: [
      'Weather, sunshine & rain probability',
      'Wave height & sea chop conditions',
      'Sea state & chop severity',
      'Coastal route conditions',
      'Environmental risk considerations',
      'Coastal marine conditions near harbour mouth'
    ],
    suggestedQuestions: [
      'What are today\'s sea conditions?',
      'Are conditions suitable for a coastal boat trip?',
      'What are the wave conditions tomorrow?',
      'Compare morning and afternoon conditions.'
    ],
    dashboardSections: [
      { id: 'marine_conditions', title: "Today's Marine Conditions", description: 'Overview of sea swell, rain likelihood, and surface winds.', priority: 1 },
      { id: 'weather', title: 'Weather & Precipitation', description: 'Hourly atmospheric forecast and rain probabilities for guests.', priority: 2 },
      { id: 'sea_state', title: 'Sea State & Wave Conditions', description: 'Wave height, swell period, and sea state evaluation for small passenger craft.', priority: 3 },
      { id: 'route_safety', title: 'Route Safety & Corridors', description: 'Safe passage corridor avoiding configured shipping channel and naval perimeters.', priority: 4 },
      { id: 'marine_risk', title: 'Marine Risk Assessment', description: 'Deterministic safety rating based on craft seaworthiness limits.', priority: 5 },
      { id: 'marine_map', title: 'Coastal Activity Map', description: 'Visual map of Fort Kochi, Vypin, and harbor mouth areas.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: false,
      showRestricted: true,
      showRoute: true,
      showVessel: true,
      highlightFocus: 'route',
      badgeText: 'Coastal Excursion Route & Harbours'
    },
    terminology: {
      riskAssessmentLabel: 'PASSENGER CRAFT OPERATIONAL SAFETY',
      routeLabel: 'COASTAL EXCURSION CORRIDOR',
      landingCenterLabel: 'Tourist Jetty / Harbour Point',
      roleDisclaimer: 'Advisory forecast decision support only. Does not guarantee calm conditions or replace certified skipper discretion.',
      actionCallout: 'Verify wave heights and rain probabilities before departure.'
    }
  },

  general_user: {
    id: 'general_user',
    displayName: 'General User',
    shortName: 'General User',
    icon: '👤',
    purpose: 'Provide the standard, versatile ORCA marine intelligence experience.',
    tagline: 'Explore marine weather, ocean conditions, PFZs & safety',
    defaultTab: '/chat',
    defaultVessel: 'motorized_frp_obm',
    priorities: [
      'Marine weather & atmospheric forecasts',
      'Ocean conditions & wave heights',
      'Potential Fishing Zones (PFZs)',
      'Vessel safety assessments',
      'Interactive marine map',
      'General coastal marine intelligence'
    ],
    suggestedQuestions: [
      'What\'s the weather today?',
      'How are the sea conditions?',
      'Show nearby PFZs.',
      'Is it safe to go fishing today?',
      'What\'s happening in the sea today?'
    ],
    dashboardSections: [
      { id: 'marine_intelligence', title: 'Marine Intelligence Overview', description: 'Comprehensive coastal conditions across weather, ocean, and GIS.', priority: 1 },
      { id: 'weather', title: 'Atmospheric Weather Observations', description: 'Wind speed, rain probability, and temperature forecasts.', priority: 2 },
      { id: 'ocean_conditions', title: 'Ocean Conditions', description: 'Significant wave height, sea state classification, and tidal trend.', priority: 3 },
      { id: 'pfz', title: 'Potential Fishing Zones', description: 'Historical INCOIS landing centre targets with distances and bearings.', priority: 4 },
      { id: 'safety', title: 'Vessel Safety Evaluation', description: 'Deterministic multi-factor risk assessment and seaworthiness rating.', priority: 5 },
      { id: 'map', title: 'Marine Sector Map', description: 'Interactive Leaflet map with spatial layers and passage corridors.', priority: 6 }
    ],
    mapEmphasis: {
      showPfz: true,
      showRestricted: true,
      showRoute: true,
      showVessel: true,
      highlightFocus: 'general',
      badgeText: 'General Marine Ecosystem Map'
    },
    terminology: {
      riskAssessmentLabel: 'ENVIRONMENTAL CONDITION RISK',
      routeLabel: 'SAFE PASSAGE CORRIDOR',
      landingCenterLabel: 'Coastal Landing Centre',
      roleDisclaimer: 'Prototype demonstration decision-support system. Not for live maritime navigation.',
      actionCallout: 'Ask ORCA about weather, ocean conditions, routes, or PFZ targets.'
    }
  }
};

export const DEFAULT_ROLE_ID: RoleId = 'general_user';

export function getRole(id: string | null | undefined): RoleConfig {
  if (id && id in ROLES_CONFIG) {
    return ROLES_CONFIG[id as RoleId];
  }
  return ROLES_CONFIG[DEFAULT_ROLE_ID];
}

export function getAllRoles(): RoleConfig[] {
  return Object.values(ROLES_CONFIG);
}

export const ROLE_STORAGE_KEY = 'orca_user_role';

export function getStoredRole(): RoleConfig {
  try {
    const stored = localStorage.getItem(ROLE_STORAGE_KEY);
    if (stored && stored in ROLES_CONFIG) {
      return ROLES_CONFIG[stored as RoleId];
    }
  } catch (err) {
    console.warn('Could not read role from localStorage:', err);
  }
  return ROLES_CONFIG[DEFAULT_ROLE_ID];
}

export function setStoredRole(roleId: RoleId): void {
  try {
    localStorage.setItem(ROLE_STORAGE_KEY, roleId);
  } catch (err) {
    console.warn('Could not save role to localStorage:', err);
  }
}
