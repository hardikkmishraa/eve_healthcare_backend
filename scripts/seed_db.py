"""
Seed script to populate the database with sample diagnostic centres and tests.
Run: python scripts/seed_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal, create_tables
from app.models.models import DiagnosticCentre, DiagnosticTest, CentreTest, User
from app.core.security import hash_password
from decimal import Decimal


def seed():
    create_tables()
    db = SessionLocal()
    try:
        # ── Skip if already seeded ────────────────────────────────────────────
        if db.query(DiagnosticCentre).count() > 0:
            print("Database already seeded. Skipping.")
            return

        print("Seeding database...")

        # ── Admin User ─────────────────────────────────────────────────────────
        from app.models.models import UserRole
        admin = User(
            email="admin@evehealthcare.com",
            hashed_password=hash_password("Admin@1234"),
            full_name="EVE Admin",
            phone_number="+919876543210",
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()
        print(f"  Created admin user: {admin.email}")

        # ── Diagnostic Centres ─────────────────────────────────────────────────
        centres_data = [
            {"name": "Apollo Diagnostics", "address": "123 Main Street, Bandra West", "city": "Mumbai", "pincode": "400050"},
            {"name": "Dr. Lal PathLabs", "address": "45 Connaught Place", "city": "Delhi", "pincode": "110001"},
            {"name": "SRL Diagnostics", "address": "78 MG Road, Indiranagar", "city": "Bangalore", "pincode": "560038"},
            {"name": "Metropolis Healthcare", "address": "12 Anna Salai", "city": "Chennai", "pincode": "600002"},
        ]
        centres = []
        for c in centres_data:
            centre = DiagnosticCentre(**c)
            db.add(centre)
            centres.append(centre)
        db.flush()
        print(f"  Created {len(centres)} diagnostic centres")

        # ── Diagnostic Tests ───────────────────────────────────────────────────
        tests_data = [
            {"name": "Complete Blood Count (CBC)", "category": "Haematology", "description": "Measures red/white blood cells, haemoglobin, and platelets", "sample_type": "Blood"},
            {"name": "Lipid Profile", "category": "Biochemistry", "description": "Measures cholesterol, triglycerides, HDL, LDL", "sample_type": "Blood"},
            {"name": "Thyroid Panel (T3, T4, TSH)", "category": "Endocrinology", "description": "Measures thyroid hormone levels", "sample_type": "Blood"},
            {"name": "Blood Glucose Fasting", "category": "Biochemistry", "description": "Measures fasting blood sugar level", "sample_type": "Blood"},
            {"name": "HbA1c (Glycated Haemoglobin)", "category": "Biochemistry", "description": "Average blood sugar over 2-3 months, used to diagnose diabetes", "sample_type": "Blood"},
            {"name": "Liver Function Test (LFT)", "category": "Biochemistry", "description": "Assesses liver health via enzyme and protein levels", "sample_type": "Blood"},
            {"name": "Kidney Function Test (KFT)", "category": "Nephrology", "description": "Evaluates kidney health - creatinine, urea, electrolytes", "sample_type": "Blood"},
            {"name": "Urine Routine & Microscopy", "category": "Microbiology", "description": "General urine analysis for infections, kidney function", "sample_type": "Urine"},
            {"name": "Chest X-Ray (PA View)", "category": "Radiology", "description": "X-ray of lungs and chest cavity", "sample_type": "Imaging"},
            {"name": "ECG (12-lead)", "category": "Cardiology", "description": "Records electrical activity of the heart", "sample_type": "Non-invasive"},
            {"name": "COVID-19 RT-PCR", "category": "Microbiology", "description": "Detects SARS-CoV-2 viral RNA", "sample_type": "Nasal Swab"},
            {"name": "Vitamin D (25-OH)", "category": "Biochemistry", "description": "Measures Vitamin D levels in blood", "sample_type": "Blood"},
        ]
        tests = []
        for t in tests_data:
            test = DiagnosticTest(**t)
            db.add(test)
            tests.append(test)
        db.flush()
        print(f"  Created {len(tests)} diagnostic tests")

        # ── Centre-Test Mappings with Pricing ──────────────────────────────────
        # Each centre offers a subset of tests at varying prices
        centre_test_prices = [
            # Apollo Mumbai — premium pricing
            (0, 0, Decimal("550.00")),   # CBC
            (0, 1, Decimal("900.00")),   # Lipid Profile
            (0, 2, Decimal("850.00")),   # Thyroid Panel
            (0, 3, Decimal("200.00")),   # Blood Glucose
            (0, 4, Decimal("700.00")),   # HbA1c
            (0, 8, Decimal("400.00")),   # Chest X-Ray
            (0, 9, Decimal("350.00")),   # ECG

            # Dr. Lal PathLabs Delhi — moderate pricing
            (1, 0, Decimal("450.00")),   # CBC
            (1, 1, Decimal("800.00")),   # Lipid Profile
            (1, 2, Decimal("750.00")),   # Thyroid Panel
            (1, 5, Decimal("950.00")),   # LFT
            (1, 6, Decimal("900.00")),   # KFT
            (1, 7, Decimal("250.00")),   # Urine Routine
            (1, 10, Decimal("1200.00")), # COVID RT-PCR

            # SRL Diagnostics Bangalore
            (2, 0, Decimal("480.00")),   # CBC
            (2, 3, Decimal("180.00")),   # Blood Glucose
            (2, 4, Decimal("650.00")),   # HbA1c
            (2, 5, Decimal("900.00")),   # LFT
            (2, 11, Decimal("1100.00")), # Vitamin D
            (2, 9, Decimal("320.00")),   # ECG

            # Metropolis Chennai
            (3, 0, Decimal("420.00")),   # CBC
            (3, 1, Decimal("750.00")),   # Lipid Profile
            (3, 6, Decimal("850.00")),   # KFT
            (3, 7, Decimal("220.00")),   # Urine Routine
            (3, 8, Decimal("380.00")),   # Chest X-Ray
            (3, 11, Decimal("1050.00")), # Vitamin D
        ]

        for centre_idx, test_idx, price in centre_test_prices:
            ct = CentreTest(
                centre_id=centres[centre_idx].id,
                test_id=tests[test_idx].id,
                price=price,
            )
            db.add(ct)

        db.commit()
        print(f"  Created {len(centre_test_prices)} centre-test mappings")
        print("\n✅ Database seeded successfully!")
        print(f"\nAdmin credentials:")
        print(f"  Email:    admin@evehealthcare.com")
        print(f"  Password: Admin@1234")

    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
