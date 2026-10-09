"""API router for Phase 6 Personalization and Human Approval."""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.schemas.personalization import PersonalizationResult, ApprovalRequest, ApprovalResponse
from app.services.personalization_service import PersonalizationService
from app.services.message_validation_service import MessageValidationService
from app.services.approval_service import ApprovalService
from app.workflows.personalization_workflow import build_personalization_graph

try:
    from app.api.website_intelligence import get_llm
except ImportError:
    def get_llm():
        from app.config import get_settings
        settings = get_settings()
        if settings.LLM_PROVIDER == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(api_key=settings.GROQ_API_KEY, model_name=settings.GROQ_MODEL)
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(google_api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/personalization", tags=["Personalization & Approval"])

@router.post(
    "/generate",
    response_model=PersonalizationResult,
    status_code=status.HTTP_200_OK
)
async def generate_personalization(
    lead_id: uuid.UUID,
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Trigger the Personalization workflow for a specific lead and campaign."""
    try:
        llm = get_llm()
    except Exception as e:
        logger.error(f"Failed to load LLM: {e}")
        raise HTTPException(status_code=500, detail="LLM configuration error")
        
    p_service = PersonalizationService(llm)
    v_service = MessageValidationService()
    
    graph = build_personalization_graph(db, p_service, v_service)
    
    initial_state = {
        "lead_id": lead_id, 
        "campaign_id": campaign_id,
        "errors": [],
        "warnings": []
    }
    
    try:
        final_state = await graph.ainvoke(initial_state)
        
        return PersonalizationResult(
            lead_id=lead_id,
            campaign_id=campaign_id,
            message_id=final_state.get("message_id"),
            status=final_state.get("approval_status", "draft"),
            validation_result=final_state.get("validation_result"),
            errors=final_state.get("errors", [])
        )
        
    except Exception as e:
        logger.error(f"Error generating personalization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/messages/{message_id}/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK
)
async def approve_message(
    message_id: uuid.UUID,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process a human approval action for a generated message."""
    approval_svc = ApprovalService(db)
    
    try:
        msg = await approval_svc.process_approval(
            message_id=message_id,
            action=request.action,
            edited_subject=request.edited_subject,
            edited_body=request.edited_body,
            reason=request.rejection_reason
        )
        
        return ApprovalResponse(
            message_id=msg.id,
            new_status=msg.status
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
