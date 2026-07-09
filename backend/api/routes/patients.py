"""
GET /patients — Demo patient registry.

Returns a static in-memory list that exactly matches the
frontend Patient TypeScript interface:

  {
    id: string;
    name: string;
    age: number;
    gender: 'Male' | 'Female' | 'Other';
    bloodType?: string;
    dateOfBirth: string;
    contactNumber?: string;
    email?: string;
    medicalHistory?: string[];
    createdAt: string;
  }

This satisfies the /patients 404 without touching the database,
Kafka pipeline, or any existing endpoints.
"""

import logging
from typing import List, Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


class Patient(BaseModel):
    id: str
    name: str
    age: int
    gender: str          # 'Male' | 'Female' | 'Other'
    bloodType: Optional[str] = None
    dateOfBirth: str
    contactNumber: Optional[str] = None
    email: Optional[str] = None
    medicalHistory: Optional[List[str]] = None
    createdAt: str


# ---------------------------------------------------------------------------
# Demo registry
# ---------------------------------------------------------------------------
# These records mirror the real PTB-XL patient IDs used by the Kafka producer
# (P001 is the live-streaming patient). Add real DB integration here later.

_DEMO_PATIENTS: List[Patient] = [
    Patient(
        id="P001",
        name="Ahmed Hassan",
        age=58,
        gender="Male",
        bloodType="A+",
        dateOfBirth="1966-03-14",
        contactNumber="+20-10-1234-5678",
        email="ahmed.hassan@demo.cardioguard.ai",
        medicalHistory=[
            "Hypertension",
            "Type 2 Diabetes",
            "Previous MI (2019)",
        ],
        createdAt="2024-01-15T08:00:00Z",
    ),
    Patient(
        id="P002",
        name="Fatma El-Sayed",
        age=44,
        gender="Female",
        bloodType="O+",
        dateOfBirth="1980-07-22",
        contactNumber="+20-11-9876-5432",
        email="fatma.elsayed@demo.cardioguard.ai",
        medicalHistory=[
            "Atrial Fibrillation",
            "Hyperlipidemia",
        ],
        createdAt="2024-02-20T10:30:00Z",
    ),
    Patient(
        id="P003",
        name="Omar Khalil",
        age=67,
        gender="Male",
        bloodType="B-",
        dateOfBirth="1957-11-05",
        contactNumber="+20-12-5555-0001",
        email="omar.khalil@demo.cardioguard.ai",
        medicalHistory=[
            "Left Bundle Branch Block",
            "Heart Failure (EF 40%)",
        ],
        createdAt="2024-03-10T14:15:00Z",
    ),
    Patient(
        id="P004",
        name="Sara Mahmoud",
        age=35,
        gender="Female",
        bloodType="AB+",
        dateOfBirth="1989-05-18",
        contactNumber="+20-10-2222-3333",
        email=None,
        medicalHistory=None,
        createdAt="2024-04-05T09:00:00Z",
    ),
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[Patient])
async def get_patients():
    """
    Return all patients in the demo registry.

    Frontend calls: GET /patients
    Returns: Patient[]
    """
    logger.debug("GET /patients → returning %d records", len(_DEMO_PATIENTS))
    return _DEMO_PATIENTS


@router.get("/{patient_id}", response_model=Patient)
async def get_patient_by_id(patient_id: str):
    """
    Return a single patient by ID.

    Frontend calls: GET /patients/{id}
    Returns: Patient
    """
    # pyrefly: ignore [missing-import]
    from fastapi import HTTPException

    for patient in _DEMO_PATIENTS:
        if patient.id == patient_id:
            return patient

    raise HTTPException(
        status_code=404,
        detail=f"Patient '{patient_id}' not found.",
    )
