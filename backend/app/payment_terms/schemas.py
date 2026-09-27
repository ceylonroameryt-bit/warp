"""
Warp Ladger — Payment Terms Pydantic Schemas
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import PaymentTermType


class PaymentTermBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name e.g. Net 30, Due immediately")
    term_type: PaymentTermType = Field(default=PaymentTermType.DAYS_AFTER_INVOICE)
    days: int = Field(default=0, ge=0, le=365, description="Number of days for term calculation")
    is_default_customer: bool = Field(default=False, description="Default for new customers")
    is_default_supplier: bool = Field(default=False, description="Default for new suppliers")
    active: bool = Field(default=True)


class PaymentTermCreate(PaymentTermBase):
    pass


class PaymentTermUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    term_type: Optional[PaymentTermType] = None
    days: Optional[int] = Field(default=None, ge=0, le=365)
    is_default_customer: Optional[bool] = None
    is_default_supplier: Optional[bool] = None
    active: Optional[bool] = None


class PaymentTermResponse(PaymentTermBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
