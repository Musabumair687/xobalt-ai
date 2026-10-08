"""API router for Lead Scoring and Intent."""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.schemas.scoring import LeadScoreResponse, IntentSignalResult
from app.services.intent_service import IntentService
from app.services.intent_signal_service import IntentSignalService
from app.services.scoring_service import ScoringService
from app.workflows.scoring_intent_workflow import build_scoring_intent_graph

# Try to reuse LLM factory from website intelligence
try:
    from app.api.website_intelligence import get_llm
except ImportError:
    # Fallback if not available
    def get_llm():
        from app.config import get_settings
        settings = get_settings()
        if settings.LLM_PROVIDER == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(api_key=settings.GROQ_API_KEY, model_name=settings.GROQ_MODEL)
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(google_api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["Scoring & Intent"])

@router.post(
    "/{lead_id}/score",
    response_model=LeadScoreResponse,
    status_code=status.HTTP_200_OK
)
async def score_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Trigger the Scoring and Intent workflow for a specific lead."""
    
    # Setup services
    try:
        llm = get_llm()
    except Exception as e:
        logger.error(f"Failed to load LLM for scoring: {e}")
        raise HTTPException(status_code=500, detail="LLM configuration error")
        
    intent_service = IntentService(llm)
    signal_service = IntentSignalService(db)
    scoring_service = ScoringService()
    
    graph = build_scoring_intent_graph(db, intent_service, signal_service, scoring_service)
    
    initial_state = {"lead_id": lead_id, "errors": []}
    
    try:
        final_state = await graph.ainvoke(initial_state)
        
        if final_state.get("errors"):
            raise HTTPException(status_code=400, detail=f"Workflow failed: {final_state['errors']}")
            
        # Format the response
        intent_signals = []
        for sig in final_state.get("validated_intent_signals", []):
            intent_signals.append(
                IntentSignalResult(
                    signal_type=sig.signal_type,
                    description=sig.description or "",
                    evidence=sig.evidence or "",
                    confidence=sig.confidence or 0.0
                )
            )
            
        return LeadScoreResponse(
            lead_id=lead_id,
            score=final_state["total_score"],
            classification=final_state["classification"],
            breakdown=final_state["score_breakdown"],
            intent_signals=intent_signals
        )
        
    except Exception as e:
        logger.error(f"Error scoring lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
