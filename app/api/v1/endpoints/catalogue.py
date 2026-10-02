from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.catalogue_service import CatalogueService
from app.schemas.catalogue import (
    DiagnosticCentreResponse, CentreWithTestsResponse,
    DiagnosticTestResponse, CentreTestResponse, CentreTestCreate,
    DiagnosticCentreCreate, DiagnosticTestCreate,
)

router = APIRouter(tags=["Centres & Tests"])


# ─── Diagnostic Centres ────────────────────────────────────────────────────────

@router.get(
    "/centres",
    response_model=dict,
    summary="List all diagnostic centres",
)
def list_centres(
    city: Optional[str] = Query(None, description="Filter by city name"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List all diagnostic centres with optional filtering.
    Supports pagination via `page` and `page_size`.
    """
    service = CatalogueService(db)
    return service.list_centres(city=city, is_active=is_active, page=page, page_size=page_size)


@router.get(
    "/centres/{centre_id}",
    response_model=DiagnosticCentreResponse,
    summary="Get a specific diagnostic centre",
)
def get_centre(centre_id: str, db: Session = Depends(get_db)):
    """Retrieve details of a specific diagnostic centre by ID."""
    service = CatalogueService(db)
    return service.get_centre(centre_id)


@router.post(
    "/centres",
    response_model=DiagnosticCentreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a diagnostic centre",
)
def create_centre(
    data: DiagnosticCentreCreate,
    _: str = Depends(get_current_user_id),  # requires auth
    db: Session = Depends(get_db),
):
    """Create a new diagnostic centre. Requires authentication."""
    service = CatalogueService(db)
    return service.create_centre(data)


# ─── Centre Tests ──────────────────────────────────────────────────────────────

@router.get(
    "/centres/{centre_id}/tests",
    response_model=List[CentreTestResponse],
    summary="List tests available at a specific centre",
)
def get_centre_tests(centre_id: str, db: Session = Depends(get_db)):
    """List all diagnostic tests offered at a specific centre, with their prices."""
    service = CatalogueService(db)
    return service.get_centre_tests(centre_id)


@router.post(
    "/centres/{centre_id}/tests",
    response_model=CentreTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Add a test to a centre with pricing",
)
def add_test_to_centre(
    centre_id: str,
    data: CentreTestCreate,
    _: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Add a diagnostic test to a centre with a specific price. Requires authentication."""
    service = CatalogueService(db)
    return service.add_test_to_centre(centre_id, data)


# ─── Diagnostic Tests ──────────────────────────────────────────────────────────

@router.get(
    "/tests",
    response_model=dict,
    summary="List all diagnostic tests",
)
def list_tests(
    category: Optional[str] = Query(None, description="Filter by test category"),
    search: Optional[str] = Query(None, description="Search by test name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all available diagnostic tests with filtering and pagination."""
    service = CatalogueService(db)
    return service.list_tests(category=category, search=search, page=page, page_size=page_size)


@router.post(
    "/tests",
    response_model=DiagnosticTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a diagnostic test",
)
def create_test(
    data: DiagnosticTestCreate,
    _: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create a new diagnostic test in the catalog. Requires authentication."""
    service = CatalogueService(db)
    return service.create_test(data)
