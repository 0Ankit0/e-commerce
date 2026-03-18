from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class StaticPageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ReportJobStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Banner(SQLModel, table=True):
    __tablename__ = "content_banners"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255)
    subtitle: str = Field(default="", max_length=500)
    image_url: str = Field(default="", max_length=500)
    cta_label: str = Field(default="", max_length=120)
    cta_url: str = Field(default="", max_length=500)
    placement: str = Field(default="home", max_length=80, index=True)
    starts_at: Optional[datetime] = Field(default=None)
    ends_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True, index=True)
    sort_order: int = Field(default=0)
    metadata_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class StaticPage(SQLModel, table=True):
    __tablename__ = "content_static_pages"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=120, unique=True, index=True)
    title: str = Field(max_length=255)
    summary: str = Field(default="", max_length=500)
    body_markdown: str = Field(default="")
    status: StaticPageStatus = Field(default=StaticPageStatus.DRAFT)
    seo_title: str = Field(default="", max_length=255)
    seo_description: str = Field(default="", max_length=500)
    published_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReportJob(SQLModel, table=True):
    __tablename__ = "admin_report_jobs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    report_type: str = Field(max_length=80, index=True)
    requested_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    date_from: Optional[datetime] = Field(default=None)
    date_to: Optional[datetime] = Field(default=None)
    filters_json: str = Field(default="{}")
    status: ReportJobStatus = Field(default=ReportJobStatus.SCHEDULED)
    output_format: str = Field(default="csv", max_length=20)
    result_url: str = Field(default="", max_length=500)
    result_preview_json: str = Field(default="{}")
    error_message: str = Field(default="", max_length=500)
    run_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
