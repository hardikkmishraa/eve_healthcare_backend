import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, List
from decimal import Decimal

from app.repositories.catalogue_repository import CatalogueRepository
from app.schemas.catalogue import (
    DiagnosticCentreCreate, CentreTestCreate, DiagnosticTestCreate,
    DiagnosticCentreResponse, DiagnosticTestResponse, CentreTestResponse,
)
from app.models.models import DiagnosticCentre, DiagnosticTest, CentreTest
from app.core.cache import (
    cache_get, cache_set, invalidate_centre_cache,
    make_centres_cache_key, make_tests_cache_key, make_centre_tests_cache_key,
)

logger = logging.getLogger(__name__)


class CatalogueService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CatalogueRepository(db)

    # ─── Centres ────────────────────────────────────────────────────────────

    def list_centres(
        self,
        city: Optional[str] = None,
        is_active: Optional[bool] = True,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        cache_key = make_centres_cache_key(city, is_active, page, page_size)

        # Try cache first
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("Centres served from cache", extra={"city": city, "page": page})
            return cached

        skip = (page - 1) * page_size
        results, total = self.repo.get_centres(city=city, is_active=is_active, skip=skip, limit=page_size)
        serialized = [DiagnosticCentreResponse.model_validate(c).model_dump() for c in results]
        response = {"total": total, "page": page, "page_size": page_size, "results": serialized}

        cache_set(cache_key, response)
        return response

    def get_centre(self, centre_id: str) -> DiagnosticCentre:
        centre = self.repo.get_centre_by_id(centre_id)
        if not centre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic centre '{centre_id}' not found",
            )
        return centre

    def create_centre(self, data: DiagnosticCentreCreate) -> DiagnosticCentre:
        centre = self.repo.create_centre(
            name=data.name, address=data.address,
            city=data.city, pincode=data.pincode,
        )
        self.db.commit()
        self.db.refresh(centre)
        invalidate_centre_cache()  # Bust stale cache on mutation
        logger.info("Centre created", extra={"centre_id": centre.id, "centre_name": centre.name})
        return centre

    # ─── Tests ──────────────────────────────────────────────────────────────

    def list_tests(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        cache_key = make_tests_cache_key(category, search, page, page_size)

        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("Tests served from cache", extra={"category": category, "search": search})
            return cached

        skip = (page - 1) * page_size
        results, total = self.repo.get_tests(category=category, search=search, skip=skip, limit=page_size)
        serialized = [DiagnosticTestResponse.model_validate(t).model_dump() for t in results]
        response = {"total": total, "page": page, "page_size": page_size, "results": serialized}

        cache_set(cache_key, response)
        return response

    def create_test(self, data: DiagnosticTestCreate) -> DiagnosticTest:
        existing = self.repo.get_test_by_name(data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Diagnostic test '{data.name}' already exists",
            )
        test = self.repo.create_test(
            name=data.name, category=data.category,
            description=data.description, sample_type=data.sample_type,
        )
        self.db.commit()
        self.db.refresh(test)
        invalidate_centre_cache()
        logger.info("Diagnostic test created", extra={"test_id": test.id, "test_name": test.name})
        return test

    # ─── Centre-Test Mappings ────────────────────────────────────────────────

    def get_centre_tests(self, centre_id: str) -> List[CentreTest]:
        self.get_centre(centre_id)

        cache_key = make_centre_tests_cache_key(centre_id)
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        results = self.repo.get_centre_tests(centre_id)
        serialized = [CentreTestResponse.model_validate(ct).model_dump() for ct in results]
        cache_set(cache_key, serialized)
        return results

    def add_test_to_centre(self, centre_id: str, data: CentreTestCreate) -> CentreTest:
        centre = self.repo.get_centre_by_id(centre_id)
        if not centre:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Centre '{centre_id}' not found")
        if not centre.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Cannot add tests to an inactive centre")
        test = self.repo.get_test_by_id(data.test_id)
        if not test:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Diagnostic test '{data.test_id}' not found")
        if self.repo.centre_test_exists(centre_id, data.test_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="This test is already listed at this centre")
        ct = self.repo.create_centre_test(centre_id, data.test_id, data.price)
        self.db.commit()
        ct = self.repo.get_centre_test_by_id(ct.id)
        # Invalidate centre-specific test cache
        from app.core.cache import cache_delete
        cache_delete(make_centre_tests_cache_key(centre_id))
        logger.info("Test added to centre", extra={"centre_id": centre_id, "test_id": data.test_id})
        return ct

    def get_centre_test_by_id(self, centre_test_id: str) -> CentreTest:
        ct = self.repo.get_centre_test_by_id(centre_test_id)
        if not ct:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Centre-test listing '{centre_test_id}' not found")
        return ct
