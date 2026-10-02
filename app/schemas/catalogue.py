from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class DiagnosticTestBase(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    sample_type: Optional[str] = None


class DiagnosticTestResponse(DiagnosticTestBase):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DiagnosticTestCreate(DiagnosticTestBase):
    pass


# ─── Centres ──────────────────────────────────────────────────────────────────

class DiagnosticCentreBase(BaseModel):
    name: str
    address: str
    city: str
    pincode: str


class DiagnosticCentreCreate(DiagnosticCentreBase):
    pass


class DiagnosticCentreResponse(DiagnosticCentreBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Centre-Test (Catalog Listing) ────────────────────────────────────────────

class CentreTestCreate(BaseModel):
    test_id: str
    price: Decimal = Field(gt=0, description="Price must be greater than 0")


class CentreTestResponse(BaseModel):
    id: str
    centre_id: str
    test_id: str
    price: Decimal
    is_available: bool
    test: DiagnosticTestResponse
    created_at: datetime

    model_config = {"from_attributes": True}


class CentreWithTestsResponse(DiagnosticCentreResponse):
    """Centre detail response including its test catalog."""
    centre_tests: List[CentreTestResponse] = []


class PaginatedResponse(BaseModel):
    """Generic paginated envelope."""
    total: int
    page: int
    page_size: int
    results: list
