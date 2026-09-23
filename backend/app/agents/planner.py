"""ORCA Marine Intelligence - Planner Agent

The PlannerAgent inspects the incoming user prompt, extracts geographic references,
temporal horizons, and operational intent, and decides which specialized agents
(Weather, Ocean, Geospatial) must be executed.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from app.models.schemas import PlannerOutput, LocationCoords, ConversationContext
from app.services.context_resolver import ContextResolver

logger = logging.getLogger("orca.agents.planner")


class PlannerAgent:
    """Planner Agent determining task decomposition and agent routing."""

    AGENT_NAME = "PlannerAgent"

    def plan(
        self,
        message: str,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        prior_context: Optional[ConversationContext] = None,
        conversation_id: Optional[str] = None,
        vessel_type: Optional[str] = None,
        language_mode: Optional[str] = None
    ) -> Tuple[PlannerOutput, ConversationContext]:
        """Parse query with context resolution and return structured plan and updated context."""
        logger.info(f"[{self.AGENT_NAME}] Analyzing message: '{message}' (vessel='{vessel_type}', lang='{language_mode}')")

        plan, updated_context = ContextResolver.resolve(
            message=message,
            prior_context=prior_context,
            user_lat=user_lat,
            user_lon=user_lon,
            conversation_id=conversation_id,
            vessel_type=vessel_type,
            language_mode=language_mode
        )

        loc_name = plan.location.name if plan.location else "None"
        logger.info(
            f"[{self.AGENT_NAME}] Plan resolved: intent='{plan.intent}', "
            f"location='{loc_name}', agents={plan.required_agents}"
        )
        return plan, updated_context

