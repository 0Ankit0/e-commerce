from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.iam.api.deps import get_db, get_optional_current_user
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.recommendations.models import RecommendationEventType, RecommendationPlacement
from src.apps.recommendations.services import get_recommendations, record_recommendation_event

router = APIRouter()


class RecommendationEventRequest(BaseModel):
    event_type: RecommendationEventType
    product_id: str | None = None
    placement: RecommendationPlacement | None = None
    query_text: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


@router.get("/recommendations")
async def fetch_recommendations(
    type: RecommendationPlacement,
    limit: int = 10,
    product_id: str | None = None,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    recommendations = await get_recommendations(
        placement=type,
        limit=limit,
        db=db,
        user_id=current_user.id if current_user else None,
        product_id=decode_id_or_404(product_id) if product_id else None,
    )
    return {"strategy": "ml_ranker_v2", "items": recommendations}


@router.post("/recommendations/events", status_code=201)
async def track_recommendation_event(
    payload: RecommendationEventRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    event = await record_recommendation_event(
        user_id=current_user.id if current_user else None,
        product_id=decode_id_or_404(payload.product_id) if payload.product_id else None,
        event_type=payload.event_type,
        placement=payload.placement,
        query_text=payload.query_text,
        metadata=payload.metadata,
        db=db,
    )
    await db.commit()
    await analytics.capture(
        str(current_user.id) if current_user else "anonymous",
        "recommendation_event",
        {"event_type": payload.event_type.value, "placement": payload.placement.value if payload.placement else None},
    )
    return {"event_id": event.id}
