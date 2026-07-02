from fastapi import APIRouter

from app.common.enums import EmploymentType, SeniorityLevel

router = APIRouter(tags=["reference"])


@router.get("/reference")
async def reference():
    return {
        "seniorityLevels": [level.value for level in SeniorityLevel],
        "employmentTypes": [etype.value for etype in EmploymentType],
    }
