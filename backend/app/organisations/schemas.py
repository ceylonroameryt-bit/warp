"""
Warp Ladger — Organisations Schemas
"""
import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateOrganisationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=100)
    currency: str = Field(default="GBP", max_length=3)
    timezone: str = Field(default="Europe/London", max_length=50)

    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[a-z0-9][a-z0-9\-]{1,98}[a-z0-9]$", v):
            raise ValueError(
                "Slug must be 2-100 lowercase letters, numbers, or hyphens, and cannot start/end with a hyphen."
            )
        return v


class UpdateOrganisationRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    company_number: Optional[str] = Field(default=None, max_length=50)
    vat_number: Optional[str] = Field(default=None, max_length=50)
    timezone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[dict] = None


class OrganisationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str]
    status: str
    currency: str
    timezone: str
    locale: str

    model_config = {"from_attributes": True}


class OrganisationDetailResponse(OrganisationResponse):
    company_number: Optional[str]
    vat_number: Optional[str]
    address: Optional[dict]
    owner_id: UUID
