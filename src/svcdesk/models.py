# ai-generated: 85% - Claude Code drafted the whole package from docs/REQUIREMENTS.md and docs/API.md, reviewed by the author
"""Request-body schemas (docs/API.md section 2 and 7). Server-owned and unknown fields are ignored, never rejected."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Reporter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=100)
    email: Optional[str] = None
    vip: bool = False


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    reporter: Reporter
    impact: Literal[1, 2, 3]
    urgency: Literal[1, 2, 3]
    related_to: Optional[str] = None
