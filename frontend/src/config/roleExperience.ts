import type { RoleId } from './roles';

export type VisualComponentType =
  | 'fishing_window'
  | 'marine_conditions'
  | 'wave_trend'
  | 'weather_trend'
  | 'risk_indicator'
  | 'route_corridor'
  | 'pfz_card';

export type MetricType =
  | 'wind'
  | 'wave'
  | 'rain'
  | 'sea_state'
  | 'tide'
  | 'sst'
  | 'risk'
  | 'pfz_distance'
  | 'fuel'
  | 'transit_duration';

export type ResponseStyle =
  | 'practical_safety'
  | 'operational_route'
  | 'situational_overview'
  | 'urgent_hazard'
  | 'analytical_scientific'
  | 'regulatory_monitoring'
  | 'environmental_compliance'
  | 'tourism_excursion'
  | 'general_accessible';

export type InformationDensity = 'compact' | 'balanced' | 'detailed';

export interface RoleChatExperience {
  roleId: RoleId;
  badgeLabel: string;
  responseHeading: string;
  responseStyle: ResponseStyle;
  informationDensity: InformationDensity;
  preferredTerminology: {
    riskAssessmentLabel: string;
    routeLabel: string;
    landingCenterLabel: string;
    promptPlaceholder: string;
  };
  priorityMetrics: MetricType[];
  visualOrder: VisualComponentType[];
  suggestedFollowUps: string[];
}

export const ROLE_CHAT_EXPERIENCES: Record<RoleId, RoleChatExperience> = {
  fisherman: {
    roleId: 'fisherman',
    badgeLabel: 'Fisherman Decision Mode',
    responseHeading: 'FISHING CRAFT OPERATIONAL OUTLOOK',
    responseStyle: 'practical_safety',
    informationDensity: 'compact',
    preferredTerminology: {
      riskAssessmentLabel: 'FISHING CRAFT SAFETY ADVISORY',
      routeLabel: 'FISHING PASSAGE CORRIDOR',
      landingCenterLabel: 'Landing Centre / Harbour',
      promptPlaceholder: 'Ask about fishing windows, PFZ targets, or sea chop...'
    },
    priorityMetrics: ['wave', 'sea_state', 'wind', 'risk', 'pfz_distance', 'rain'],
    visualOrder: ['fishing_window', 'marine_conditions', 'pfz_card', 'risk_indicator'],
    suggestedFollowUps: [
      'When is the better fishing window today?',
      'Show nearby PFZs within 30 km.',
      'What are the wave conditions tomorrow morning?'
    ]
  },

  vessel_operator: {
    roleId: 'vessel_operator',
    badgeLabel: 'Navigation & Vessel Operations',
    responseHeading: 'PASSAGE PLANNING & CORRIDOR ASSESSMENT',
    responseStyle: 'operational_route',
    informationDensity: 'balanced',
    preferredTerminology: {
      riskAssessmentLabel: 'VESSEL SEAWORTHINESS & TRANSIT RISK',
      routeLabel: 'NAVIGATION CORRIDOR (1.5 KM BUFFER)',
      landingCenterLabel: 'Departure Terminal / Harbour',
      promptPlaceholder: 'Ask about passage routes, fuel estimates, or clearance...'
    },
    priorityMetrics: ['fuel', 'transit_duration', 'wave', 'wind', 'risk', 'sea_state'],
    visualOrder: ['route_corridor', 'marine_conditions', 'wave_trend', 'risk_indicator'],
    suggestedFollowUps: [
      'Show a safe passage corridor.',
      'Are there restricted zones on this route?',
      'How long will this transit take at cruising speed?'
    ]
  },

  port_authority: {
    roleId: 'port_authority',
    badgeLabel: 'Port & Sector Situational Awareness',
    responseHeading: 'PORT SECTOR SITUATIONAL OVERVIEW',
    responseStyle: 'situational_overview',
    informationDensity: 'balanced',
    preferredTerminology: {
      riskAssessmentLabel: 'COASTAL OPERATIONAL HAZARD INDEX',
      routeLabel: 'MONITORED TRANSIT CHANNEL',
      landingCenterLabel: 'Port Sector / Harbour Master Basin',
      promptPlaceholder: 'Ask about sector risk, restricted perimeters, or swell...'
    },
    priorityMetrics: ['risk', 'wind', 'wave', 'tide', 'sea_state', 'rain'],
    visualOrder: ['risk_indicator', 'marine_conditions', 'route_corridor', 'weather_trend'],
    suggestedFollowUps: [
      'What are the current marine risk conditions?',
      'Show restricted maritime zones.',
      'Which coastal areas require caution?'
    ]
  },

  search_and_rescue: {
    roleId: 'search_and_rescue',
    badgeLabel: 'Emergency & SAR Environmental Response',
    responseHeading: 'RAPID ENVIRONMENTAL HAZARD ASSESSMENT',
    responseStyle: 'urgent_hazard',
    informationDensity: 'compact',
    preferredTerminology: {
      riskAssessmentLabel: 'EMERGENCY ENVIRONMENTAL RISK INDEX',
      routeLabel: 'RESPONSE PASSAGE CORRIDOR',
      landingCenterLabel: 'Response Staging Harbour',
      promptPlaceholder: 'Ask about adverse sea state, route hazards, or wind gusts...'
    },
    priorityMetrics: ['wave', 'wind', 'sea_state', 'risk', 'transit_duration'],
    visualOrder: ['wave_trend', 'weather_trend', 'route_corridor', 'risk_indicator'],
    suggestedFollowUps: [
      'What are the current sea and swell conditions?',
      'Which route has fewer configured hazards?',
      'What are the environmental conditions around Kochi?'
    ]
  },

  marine_researcher: {
    roleId: 'marine_researcher',
    badgeLabel: 'Oceanographic Hydrodynamics & Evidence',
    responseHeading: 'OCEANOGRAPHIC HYDRODYNAMICS & PROVENANCE',
    responseStyle: 'analytical_scientific',
    informationDensity: 'detailed',
    preferredTerminology: {
      riskAssessmentLabel: 'ENVIRONMENTAL HYDRODYNAMIC METRICS',
      routeLabel: 'OBSERVATIONAL TRANSECT',
      landingCenterLabel: 'Sampling / Reference Landing Point',
      promptPlaceholder: 'Ask about wave period, SST, tidal trends, or deltas...'
    },
    priorityMetrics: ['wave', 'sst', 'tide', 'wind', 'risk', 'rain'],
    visualOrder: ['marine_conditions', 'weather_trend', 'fishing_window', 'risk_indicator'],
    suggestedFollowUps: [
      'Compare today\'s morning and afternoon conditions.',
      'What is the current wave height and swell period?',
      'How is the sea-level trend changing?'
    ]
  },

  fisheries_officer: {
    roleId: 'fisheries_officer',
    badgeLabel: 'Fisheries Sector & PFZ Monitoring',
    responseHeading: 'FISHERIES ADVISORY & PFZ TARGET ANALYSIS',
    responseStyle: 'regulatory_monitoring',
    informationDensity: 'balanced',
    preferredTerminology: {
      riskAssessmentLabel: 'FISHERIES SECTOR RISK EVALUATION',
      routeLabel: 'FISHING TRANSIT CORRIDOR',
      landingCenterLabel: 'Designated Coastal Landing Centre',
      promptPlaceholder: 'Ask about PFZ coordinates, landing centers, or safe windows...'
    },
    priorityMetrics: ['pfz_distance', 'wave', 'sea_state', 'wind', 'risk'],
    visualOrder: ['pfz_card', 'marine_conditions', 'fishing_window', 'risk_indicator'],
    suggestedFollowUps: [
      'Show PFZ targets near Kochi.',
      'Compare available PFZ targets.',
      'Which PFZ is closest to Munambam?'
    ]
  },

  environmental_officer: {
    roleId: 'environmental_officer',
    badgeLabel: 'Coastal Conservation & Perimeter Awareness',
    responseHeading: 'COASTAL ENVIRONMENTAL INDICATOR PROFILE',
    responseStyle: 'environmental_compliance',
    informationDensity: 'detailed',
    preferredTerminology: {
      riskAssessmentLabel: 'ENVIRONMENTAL SWELL & WEATHER INDEX',
      routeLabel: 'MONITORED TRANSIT PATH',
      landingCenterLabel: 'Coastal Ecosystem Sector',
      promptPlaceholder: 'Ask about marine indicators, restricted enclaves, or SST...'
    },
    priorityMetrics: ['sst', 'tide', 'wave', 'wind', 'risk', 'rain'],
    visualOrder: ['marine_conditions', 'route_corridor', 'weather_trend', 'risk_indicator'],
    suggestedFollowUps: [
      'What are the current ocean conditions?',
      'Show restricted marine areas.',
      'What verified environmental indicators are available?'
    ]
  },

  tourism_operator: {
    roleId: 'tourism_operator',
    badgeLabel: 'Maritime Tourism & Excursion Planning',
    responseHeading: 'COASTAL EXCURSION & GUEST SEA SAFETY',
    responseStyle: 'tourism_excursion',
    informationDensity: 'compact',
    preferredTerminology: {
      riskAssessmentLabel: 'PASSENGER CRAFT OPERATIONAL SAFETY',
      routeLabel: 'COASTAL EXCURSION CORRIDOR',
      landingCenterLabel: 'Tourist Jetty / Harbour Point',
      promptPlaceholder: 'Ask about boat trip safety, rain probability, or wave chop...'
    },
    priorityMetrics: ['rain', 'wave', 'wind', 'sea_state', 'risk'],
    visualOrder: ['weather_trend', 'wave_trend', 'risk_indicator', 'route_corridor'],
    suggestedFollowUps: [
      'Are conditions suitable for a coastal boat trip?',
      'What are today\'s sea and chop conditions?',
      'Compare morning and afternoon conditions.'
    ]
  },

  general_user: {
    roleId: 'general_user',
    badgeLabel: 'General Marine Intelligence',
    responseHeading: 'MARINE INTELLIGENCE SUMMARY',
    responseStyle: 'general_accessible',
    informationDensity: 'balanced',
    preferredTerminology: {
      riskAssessmentLabel: 'ENVIRONMENTAL CONDITION RISK',
      routeLabel: 'SAFE PASSAGE CORRIDOR',
      landingCenterLabel: 'Coastal Landing Centre',
      promptPlaceholder: 'Ask ORCA about weather, ocean conditions, routes, or PFZs...'
    },
    priorityMetrics: ['wind', 'wave', 'sea_state', 'rain', 'risk', 'pfz_distance'],
    visualOrder: ['marine_conditions', 'wave_trend', 'risk_indicator', 'pfz_card'],
    suggestedFollowUps: [
      'What\'s the weather today?',
      'How are the sea conditions?',
      'Show nearby PFZs.'
    ]
  }
};

export function getRoleChatExperience(roleId?: string | null): RoleChatExperience {
  if (roleId && roleId in ROLE_CHAT_EXPERIENCES) {
    return ROLE_CHAT_EXPERIENCES[roleId as RoleId];
  }
  return ROLE_CHAT_EXPERIENCES.general_user;
}
