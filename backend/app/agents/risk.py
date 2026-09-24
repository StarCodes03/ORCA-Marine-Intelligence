"""ORCA Marine Intelligence - Risk Assessment Agent

Deterministic, rule-based calculation synthesizing weather, oceanographic,
and geospatial features to assess marine navigation and artisanal fishing safety.
All evaluation criteria strictly adhere to config/risk_thresholds.py.
"""

import logging
from typing import Optional, List, Tuple
from app.models.schemas import (
    WeatherData,
    OceanData,
    GeospatialData,
    RiskAssessment,
    RiskEvidenceItem,
    ScoreFactorItem,
    ScoreBreakdown
)
from app.config.risk_thresholds import (
    WIND_THRESHOLDS,
    WAVE_HEIGHT_THRESHOLDS,
    RAIN_PROBABILITY_THRESHOLDS,
    LIGHTNING_RISK_SCORES,
    SEA_STATE_SCORES,
    RESTRICTED_ZONE_THRESHOLDS,
    RISK_LEVEL_CUTOFFS,
    get_vessel_profile
)

logger = logging.getLogger("orca.agents.risk")


class RiskAssessmentAgent:
    """Calculates transparent, rule-based marine risk profiles."""

    AGENT_NAME = "RiskAssessmentAgent"

    def assess(
        self,
        weather: Optional[WeatherData],
        ocean: Optional[OceanData],
        geospatial: Optional[GeospatialData],
        vessel_type: Optional[str] = None
    ) -> RiskAssessment:
        """Evaluate all available sensor and spatial data against configured safety thresholds."""
        logger.info(f"[{self.AGENT_NAME}] Starting rule-based risk assessment (craft='{vessel_type}').")

        total_score: float = 0.0
        reasons: List[str] = []
        evidence: List[RiskEvidenceItem] = []
        breakdown_factors: List[ScoreFactorItem] = []
        breakdown_dict: dict = {}

        v_prof = get_vessel_profile(vessel_type)
        if v_prof:
            wind_safe_max = v_prof["wind_max_safe"]
            wind_moderate_max = v_prof["wind_max_moderate"]
            wave_safe_max = v_prof["wave_max_safe"]
            wave_moderate_max = v_prof["wave_max_moderate"]
            craft_label = f" for {v_prof['name']}"
        else:
            wind_safe_max = WIND_THRESHOLDS["safe_max"]
            wind_moderate_max = WIND_THRESHOLDS["high_max"]
            wave_safe_max = WAVE_HEIGHT_THRESHOLDS["safe_max"]
            wave_moderate_max = WAVE_HEIGHT_THRESHOLDS["high_max"]
            craft_label = ""

        # 1. Wind Speed Evaluation
        if weather:
            wind = weather.wind_speed_kmh
            if wind > wind_moderate_max:
                wind_contrib = 4.0
                total_score += wind_contrib
                threshold_str = f"> {wind_moderate_max}"
                reasons.append(f"Gale / High wind speed ({wind} km/h > {wind_moderate_max} km/h){craft_label}")
            elif wind > wind_safe_max:
                wind_contrib = 2.5
                total_score += wind_contrib
                threshold_str = f"> {wind_safe_max}"
                reasons.append(f"Elevated wind speed ({wind} km/h > {wind_safe_max} km/h){craft_label}")
            else:
                wind_contrib = 0.0
                threshold_str = f"<= {wind_safe_max}"

            evidence.append(RiskEvidenceItem(
                metric="wind_speed_kmh",
                value=wind,
                threshold=threshold_str,
                contribution=wind_contrib,
                source=weather.source
            ))
            breakdown_factors.append(ScoreFactorItem(
                factor="wind_speed",
                metric="wind_speed_kmh",
                value=f"{wind} km/h",
                threshold=threshold_str,
                contribution=wind_contrib
            ))
            breakdown_dict["wind_speed"] = wind_contrib

            # Rain Probability
            rain = weather.rain_probability
            if rain > RAIN_PROBABILITY_THRESHOLDS["moderate_max"]:
                rain_contrib = 1.5
                total_score += rain_contrib
                threshold_str = f"> {RAIN_PROBABILITY_THRESHOLDS['moderate_max']}%"
                reasons.append(f"High rain probability ({rain}% > {RAIN_PROBABILITY_THRESHOLDS['moderate_max']}%)")
            elif rain > RAIN_PROBABILITY_THRESHOLDS["low_max"]:
                rain_contrib = 0.5
                total_score += rain_contrib
                threshold_str = f"> {RAIN_PROBABILITY_THRESHOLDS['low_max']}%"
            else:
                rain_contrib = 0.0
                threshold_str = f"<= {RAIN_PROBABILITY_THRESHOLDS['low_max']}%"

            evidence.append(RiskEvidenceItem(
                metric="rain_probability",
                value=rain,
                threshold=threshold_str,
                contribution=rain_contrib,
                source=weather.source
            ))
            breakdown_factors.append(ScoreFactorItem(
                factor="rain_probability",
                metric="rain_probability",
                value=f"{rain}%",
                threshold=threshold_str,
                contribution=rain_contrib
            ))
            breakdown_dict["rain_probability"] = rain_contrib

            # Lightning Risk
            l_risk = (weather.lightning_risk or "").lower()
            if l_risk in ["unsupported", "unavailable", "not_provided", "n/a"]:
                lightning_contrib = 0.0
                threshold_str = "N/A (unsupported by live source)"
                lightning_val = "unsupported"
            else:
                l_score = LIGHTNING_RISK_SCORES.get(l_risk, 0)
                if l_score >= 2:
                    lightning_contrib = float(l_score)
                    total_score += lightning_contrib
                    threshold_str = ">= moderate"
                    if l_score == 2:
                        reasons.append("Moderate lightning risk")
                    else:
                        reasons.append(f"{weather.lightning_risk.title()} lightning risk")
                else:
                    lightning_contrib = 0.0
                    threshold_str = "low"
                lightning_val = weather.lightning_risk

            evidence.append(RiskEvidenceItem(
                metric="lightning_risk",
                value=lightning_val,
                threshold=threshold_str,
                contribution=lightning_contrib,
                source=weather.source
            ))
            breakdown_factors.append(ScoreFactorItem(
                factor="lightning_risk",
                metric="lightning_risk",
                value=lightning_val,
                threshold=threshold_str,
                contribution=lightning_contrib
            ))
            breakdown_dict["lightning_risk"] = lightning_contrib

        # 2. Wave Height & Sea State Evaluation
        if ocean:
            waves = ocean.wave_height_m
            if waves > wave_moderate_max:
                wave_contrib = 4.0
                total_score += wave_contrib
                threshold_str = f"> {wave_moderate_max} m"
                reasons.append(f"Dangerous wave height ({waves} m > {wave_moderate_max} m){craft_label}")
            elif waves > wave_safe_max:
                wave_contrib = 2.0
                total_score += wave_contrib
                threshold_str = f"> {wave_safe_max} m"
                reasons.append(f"Moderate wave height ({waves} m > {wave_safe_max} m){craft_label}")
            else:
                wave_contrib = 0.0
                threshold_str = f"<= {wave_safe_max} m"

            evidence.append(RiskEvidenceItem(
                metric="wave_height_m",
                value=waves,
                threshold=threshold_str,
                contribution=wave_contrib,
                source=ocean.source
            ))
            breakdown_factors.append(ScoreFactorItem(
                factor="wave_height",
                metric="wave_height_m",
                value=f"{waves} m",
                threshold=threshold_str,
                contribution=wave_contrib
            ))
            breakdown_dict["wave_height"] = wave_contrib

            # Sea state score
            sea_score = SEA_STATE_SCORES.get(ocean.sea_state.lower(), 1)
            if sea_score >= 3:
                sea_contrib = 2.0
                total_score += sea_contrib
                reasons.append(f"Rough sea state condition ({ocean.sea_state})")
                evidence.append(RiskEvidenceItem(
                    metric="sea_state",
                    value=ocean.sea_state,
                    threshold=">= rough",
                    contribution=sea_contrib,
                    source=ocean.source
                ))
            else:
                sea_contrib = 0.0
                evidence.append(RiskEvidenceItem(
                    metric="sea_state",
                    value=ocean.sea_state,
                    threshold="< rough",
                    contribution=sea_contrib,
                    source=ocean.source
                ))
            breakdown_factors.append(ScoreFactorItem(
                factor="sea_state",
                metric="sea_state",
                value=ocean.sea_state,
                threshold=">= rough" if sea_score >= 3 else "< rough",
                contribution=sea_contrib
            ))
            breakdown_dict["sea_state"] = sea_contrib

        # 3. Restricted Maritime Zone Proximity Evaluation
        if geospatial:
            rz = geospatial.restricted_zone_check
            if rz.inside_restricted_zone:
                rz_contrib = RESTRICTED_ZONE_THRESHOLDS["inside_penalty_score"]
                total_score += rz_contrib
                threshold_str = "inside polygon"
                reasons.append(f"VESSEL VIOLATION: Location is inside restricted maritime zone '{rz.zone_name}'")
                evidence.append(RiskEvidenceItem(
                    metric="restricted_zone",
                    value=rz.zone_name or "Unknown Zone",
                    threshold=threshold_str,
                    contribution=rz_contrib,
                    source=geospatial.source
                ))
                breakdown_factors.append(ScoreFactorItem(
                    factor="restricted_zone_violation",
                    metric="restricted_zone",
                    value=rz.zone_name or "Unknown Zone",
                    threshold=threshold_str,
                    contribution=rz_contrib
                ))
                breakdown_dict["restricted_zone"] = rz_contrib
            elif rz.restricted_zone_nearby:
                rz_contrib = 1.5
                total_score += rz_contrib
                threshold_str = f"< {RESTRICTED_ZONE_THRESHOLDS['buffer_warning_km']} km"
                reasons.append(f"Proximity alert: Near restricted zone '{rz.zone_name}' ({rz.distance_to_nearest_zone_km} km)")
                evidence.append(RiskEvidenceItem(
                    metric="restricted_zone_proximity",
                    value=f"{rz.distance_to_nearest_zone_km} km",
                    threshold=threshold_str,
                    contribution=rz_contrib,
                    source=geospatial.source
                ))
                breakdown_factors.append(ScoreFactorItem(
                    factor="restricted_zone_proximity",
                    metric="restricted_zone_proximity",
                    value=f"{rz.distance_to_nearest_zone_km} km",
                    threshold=threshold_str,
                    contribution=rz_contrib
                ))
                breakdown_dict["restricted_zone_proximity"] = rz_contrib
            else:
                rz_contrib = 0.0
                threshold_str = f">= {RESTRICTED_ZONE_THRESHOLDS['buffer_warning_km']} km"
                evidence.append(RiskEvidenceItem(
                    metric="restricted_zone_proximity",
                    value="Clear",
                    threshold=threshold_str,
                    contribution=rz_contrib,
                    source=geospatial.source
                ))
                breakdown_factors.append(ScoreFactorItem(
                    factor="restricted_zone_proximity",
                    metric="restricted_zone_proximity",
                    value="Clear",
                    threshold=threshold_str,
                    contribution=rz_contrib
                ))
                breakdown_dict["restricted_zone_proximity"] = rz_contrib

        # 4. Map Total Score to Risk Level
        risk_level = "LOW"
        for cutoff, level in RISK_LEVEL_CUTOFFS:
            if total_score <= cutoff:
                risk_level = level
                break

        if not reasons:
            reasons.append("All observed marine meteorological and ocean parameters within safe baseline limits.")

        # Environmental risk score is deterministic on a standard 0.0 - 10.0 composite scale.
        # Bounded to [0.0, 10.0] so displayed representation (Score X/10) is mathematically consistent.
        bounded_score = round(min(max(total_score, 0.0), 10.0), 1)

        score_breakdown = ScoreBreakdown(
            factors=breakdown_factors,
            factor_scores=breakdown_dict,
            total_score=bounded_score
        )

        assessment = RiskAssessment(
            risk_level=risk_level,
            risk_score=bounded_score,
            vessel_type=vessel_type,
            reasons=reasons,
            evidence=evidence,
            score_breakdown=score_breakdown
        )

        logger.info(
            f"[{self.AGENT_NAME}] Assessment complete: Level={risk_level} (score={assessment.risk_score}), "
            f"Factors={len(reasons)}, Breakdown={score_breakdown.factor_scores}"
        )
        return assessment
