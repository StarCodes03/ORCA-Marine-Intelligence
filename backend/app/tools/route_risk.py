"""ORCA Marine Intelligence - Prototype Route Risk Index Engine (M5)

Calculates the deterministic Prototype Route Risk Index (0–10) across 4 weighted dimensions:
1. Environmental conditions at the selected evaluation point (origin).
2. Vessel seaworthiness stress ratios (wave & wind) with explainable piecewise penalty.
3. Route distance exposure (nautical miles).
4. Route geofence intersection & corridor avoidance complexity.

CRITICAL DISCLAIMER:
The Prototype Route Risk Index is a configurable prototype decision-support metric;
it is NOT an official maritime safety rating, seaworthiness certification, or regulatory limit.
"""

from typing import Dict, Any, Optional, List
import logging

from app.models.schemas import (
    LocationCoords,
    RouteRiskAssessment,
    TransitRoute,
    WeatherData,
    OceanData,
    RiskAssessment
)
from app.config.risk_thresholds import (
    PROTOTYPE_ROUTE_RISK_CONFIG,
    get_vessel_profile,
    WIND_THRESHOLDS,
    WAVE_HEIGHT_THRESHOLDS
)

logger = logging.getLogger("orca.tools.route_risk")


class RouteRiskCalculator:
    """Deterministic calculator for the Prototype Route Risk Index (0–10)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or dict(PROTOTYPE_ROUTE_RISK_CONFIG)

    def calculate_vessel_stress_penalty(
        self,
        wave_height_m: float,
        wind_speed_kmh: float,
        vessel_type: Optional[str]
    ) -> Dict[str, Any]:
        """Calculate wave and wind stress ratios and explainable piecewise stress penalty."""
        v_prof = get_vessel_profile(vessel_type)
        if v_prof:
            wave_limit = float(v_prof["wave_max_safe"])
            wind_limit = float(v_prof["wind_max_safe"])
            craft_name = v_prof["name"]
        else:
            wave_limit = float(WAVE_HEIGHT_THRESHOLDS["safe_max"])
            wind_limit = float(WIND_THRESHOLDS["safe_max"])
            craft_name = "Baseline Standard Craft"

        wave_stress_ratio = round(wave_height_m / wave_limit, 2) if wave_limit > 0 else 1.0
        wind_stress_ratio = round(wind_speed_kmh / wind_limit, 2) if wind_limit > 0 else 1.0

        max_ratio = max(wave_stress_ratio, wind_stress_ratio)

        # Explainable Piecewise Penalty Model:
        # 1. ratio < 1.0: Operating comfortably within configured prototype limit (0.0 to 2.0 penalty)
        if max_ratio < 1.0:
            penalty = round(2.0 * max_ratio, 1)
            reason = (
                f"Operating within configured prototype limits for {craft_name} "
                f"(wave ratio: {wave_stress_ratio}, wind ratio: {wind_stress_ratio})."
            )
        # 2. ratio == 1.0: Operating right at configured limit boundary (3.5 penalty)
        elif max_ratio == 1.0:
            penalty = 3.5
            reason = (
                f"Operating at exact boundary of configured prototype limits for {craft_name} "
                f"(wave ratio: {wave_stress_ratio}, wind ratio: {wind_stress_ratio})."
            )
        # 3. ratio > 1.0: Exceeds configured limit (5.0 base + linear step up to 10.0)
        else:
            excess_factor = min((max_ratio - 1.0) / 0.5, 1.0)
            penalty = round(5.0 + 5.0 * excess_factor, 1)
            exceeded = []
            if wave_stress_ratio > 1.0:
                exceeded.append(f"wave {wave_height_m}m > limit {wave_limit}m (ratio {wave_stress_ratio})")
            if wind_stress_ratio > 1.0:
                exceeded.append(f"wind {wind_speed_kmh}km/h > limit {wind_limit}km/h (ratio {wind_stress_ratio})")
            reason = (
                f"Exceeds configured prototype limit for {craft_name}: {', '.join(exceeded)}."
            )

        return {
            "penalty_score": min(penalty, 10.0),
            "wave_stress_ratio": wave_stress_ratio,
            "wind_stress_ratio": wind_stress_ratio,
            "max_ratio": max_ratio,
            "reason": reason
        }

    def calculate_distance_exposure_penalty(self, distance_nm: float) -> Dict[str, Any]:
        """Calculate route exposure penalty (0–10) based on nautical distance."""
        dist = max(float(distance_nm), 0.0)
        if dist <= 10.0:
            penalty = 1.0
            reason = f"Short coastal transit ({dist:.1f} nm <= 10 nm): minimal offshore exposure."
        elif dist <= 25.0:
            fraction = (dist - 10.0) / 15.0
            penalty = round(1.0 + 4.0 * fraction, 1)
            reason = f"Moderate coastal passage ({dist:.1f} nm): moderate offshore exposure."
        else:
            excess = min((dist - 25.0) / 25.0, 1.0)
            penalty = round(5.0 + 5.0 * excess, 1)
            reason = f"Extended offshore transit ({dist:.1f} nm > 25 nm): elevated exposure."

        return {
            "penalty_score": min(penalty, 10.0),
            "reason": reason
        }

    def calculate_geofence_interaction_penalty(
        self,
        route: TransitRoute
    ) -> Dict[str, Any]:
        """Calculate route geofence intersection penalty (0–10)."""
        if not route.geofence_avoidance_applied:
            return {
                "penalty_score": 0.0,
                "reason": "Direct route clear of restricted maritime zones (no detour required)."
            }

        base_penalty = 4.0
        buffer_km = float(route.clearance_buffer_km or 1.5)
        tightness_add = 2.0 if buffer_km < 2.0 else 0.0
        total_penalty = round(base_penalty + tightness_add, 1)
        avoided_str = ", ".join(route.avoided_zones) if route.avoided_zones else "restricted perimeter"

        reason = (
            f"Direct-route restricted-zone intersection active: corridor diverted around {avoided_str} "
            f"with {buffer_km} km clearance margin."
        )

        return {
            "penalty_score": min(total_penalty, 10.0),
            "reason": reason
        }

    def assess_route_risk(
        self,
        origin: LocationCoords,
        transit_route: TransitRoute,
        weather: Optional[WeatherData],
        ocean: Optional[OceanData],
        risk_assessment: Optional[RiskAssessment],
        vessel_type: Optional[str] = None
    ) -> RouteRiskAssessment:
        """Compute the composite Prototype Route Risk Index (0–10) with explainable breakdown."""
        w_env = float(self.config.get("weight_env", 0.35))
        w_vessel = float(self.config.get("weight_vessel", 0.25))
        w_dist = float(self.config.get("weight_dist", 0.20))
        w_geom = float(self.config.get("weight_geom", 0.20))

        reasons: List[str] = []

        # 1. Environmental Base at Evaluation Point (Origin)
        # Explicit note: Evaluated strictly at origin evaluation point, not fabricated across unmeasured track points.
        if risk_assessment:
            s_env = min(float(risk_assessment.risk_score), 10.0)
            reasons.append(
                f"Environmental risk at evaluation point ({origin.name}): score {s_env} "
                f"({risk_assessment.risk_level})."
            )
        else:
            s_env = 2.0
            reasons.append(f"Environmental baseline estimated at evaluation point ({origin.name}).")

        # 2. Vessel Seaworthiness Stress Ratio
        wave_val = float(ocean.wave_height_m) if ocean and ocean.wave_height_m is not None else 1.0
        wind_val = float(weather.wind_speed_kmh) if weather and weather.wind_speed_kmh is not None else 15.0
        v_stress = self.calculate_vessel_stress_penalty(wave_val, wind_val, vessel_type)
        s_vessel = v_stress["penalty_score"]
        reasons.append(v_stress["reason"])

        # 3. Route Distance Exposure
        dist_exposure = self.calculate_distance_exposure_penalty(transit_route.total_distance_nm)
        s_dist = dist_exposure["penalty_score"]
        reasons.append(dist_exposure["reason"])

        # 4. Route Geofence Interaction
        geom_interaction = self.calculate_geofence_interaction_penalty(transit_route)
        s_geom = geom_interaction["penalty_score"]
        reasons.append(geom_interaction["reason"])

        # Composite Calculation
        contrib_env = round(w_env * s_env, 2)
        contrib_vessel = round(w_vessel * s_vessel, 2)
        contrib_dist = round(w_dist * s_dist, 2)
        contrib_geom = round(w_geom * s_geom, 2)

        raw_index = contrib_env + contrib_vessel + contrib_dist + contrib_geom
        total_index = round(min(max(raw_index, 0.0), 10.0), 1)

        # Factor contributions breakdown
        factor_breakdown = {
            "environmental_factor": contrib_env,
            "vessel_stress_factor": contrib_vessel,
            "distance_exposure_factor": contrib_dist,
            "geofence_interaction_factor": contrib_geom,
            "weight_env": w_env,
            "weight_vessel": w_vessel,
            "weight_dist": w_dist,
            "weight_geom": w_geom
        }

        # Identify dominant limiting factor
        scores = [
            (s_env, "environmental_conditions"),
            (s_vessel, "vessel_prototype_limits"),
            (s_dist, "distance_exposure"),
            (s_geom, "restricted_zone_interaction")
        ]
        scores.sort(key=lambda x: x[0], reverse=True)
        limiting_factor = scores[0][1]

        # Classification
        if total_index <= 3.0:
            risk_level = "LOW"
        elif total_index <= 6.0:
            risk_level = "MODERATE"
        elif total_index <= 8.5:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        disclaimer = str(self.config.get("disclaimer", PROTOTYPE_ROUTE_RISK_CONFIG["disclaimer"]))

        return RouteRiskAssessment(
            prototype_route_risk_index=total_index,
            risk_level=risk_level,
            evaluation_point=origin,
            vessel_type=vessel_type,
            wave_stress_ratio=v_stress["wave_stress_ratio"],
            wind_stress_ratio=v_stress["wind_stress_ratio"],
            factor_breakdown=factor_breakdown,
            limiting_factor=limiting_factor,
            reasons=reasons,
            disclaimer=disclaimer
        )


# Singleton instance
route_risk_calculator = RouteRiskCalculator()
