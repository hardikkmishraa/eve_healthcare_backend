from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from decimal import Decimal
from app.models.models import DiagnosticCentre, DiagnosticTest, CentreTest


class CatalogueRepository:
    def __init__(self, db: Session):
        self.db = db

    # ─── Centres ────────────────────────────────────────────────────────────

    def get_centres(
        self,
        city: Optional[str] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[DiagnosticCentre], int]:
        query = self.db.query(DiagnosticCentre)
        if city:
            query = query.filter(DiagnosticCentre.city.ilike(f"%{city}%"))
        if is_active is not None:
            query = query.filter(DiagnosticCentre.is_active == is_active)
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def get_centre_by_id(self, centre_id: str) -> Optional[DiagnosticCentre]:
        return (
            self.db.query(DiagnosticCentre)
            .filter(DiagnosticCentre.id == centre_id)
            .first()
        )

    def create_centre(
        self,
        name: str,
        address: str,
        city: str,
        pincode: str,
    ) -> DiagnosticCentre:
        centre = DiagnosticCentre(name=name, address=address, city=city, pincode=pincode)
        self.db.add(centre)
        self.db.flush()
        return centre

    # ─── Diagnostic Tests ────────────────────────────────────────────────────

    def get_tests(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[DiagnosticTest], int]:
        query = self.db.query(DiagnosticTest)
        if category:
            query = query.filter(DiagnosticTest.category.ilike(f"%{category}%"))
        if search:
            query = query.filter(DiagnosticTest.name.ilike(f"%{search}%"))
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def get_test_by_id(self, test_id: str) -> Optional[DiagnosticTest]:
        return self.db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()

    def get_test_by_name(self, name: str) -> Optional[DiagnosticTest]:
        return self.db.query(DiagnosticTest).filter(DiagnosticTest.name == name).first()

    def create_test(
        self,
        name: str,
        category: str,
        description: Optional[str] = None,
        sample_type: Optional[str] = None,
    ) -> DiagnosticTest:
        test = DiagnosticTest(
            name=name, category=category,
            description=description, sample_type=sample_type,
        )
        self.db.add(test)
        self.db.flush()
        return test

    # ─── Centre-Test Mappings ────────────────────────────────────────────────

    def get_centre_tests(self, centre_id: str) -> List[CentreTest]:
        return (
            self.db.query(CentreTest)
            .options(joinedload(CentreTest.test))
            .filter(CentreTest.centre_id == centre_id)
            .all()
        )

    def get_centre_test_by_id(self, centre_test_id: str) -> Optional[CentreTest]:
        return (
            self.db.query(CentreTest)
            .options(joinedload(CentreTest.test), joinedload(CentreTest.centre))
            .filter(CentreTest.id == centre_test_id)
            .first()
        )

    def create_centre_test(
        self, centre_id: str, test_id: str, price: Decimal
    ) -> CentreTest:
        ct = CentreTest(centre_id=centre_id, test_id=test_id, price=price)
        self.db.add(ct)
        self.db.flush()
        return ct

    def centre_test_exists(self, centre_id: str, test_id: str) -> bool:
        return (
            self.db.query(CentreTest.id)
            .filter(CentreTest.centre_id == centre_id, CentreTest.test_id == test_id)
            .first()
        ) is not None
