from datetime import datetime

from pydantic import BaseModel

from app.common.enums import EmploymentType, SeniorityLevel


class PostingOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    location: str | None = None
    seniority: SeniorityLevel | None = None
    employmentType: EmploymentType | None = None
    salaryMin: float | None = None
    salaryMax: float | None = None
    salaryCurrency: str | None = None
    url: str
    postedAt: datetime
    closingAt: datetime | None = None
    isActive: bool
    employerId: int
    employerName: str
    categoryId: int | None = None
    categoryName: str | None = None
    sourceSlug: str

    @classmethod
    def from_orm_obj(cls, obj):
        return cls(
            id=obj.id,
            title=obj.title,
            description=obj.description,
            location=obj.location,
            seniority=obj.seniority,
            employmentType=obj.employment_type,
            salaryMin=float(obj.salary_min) if obj.salary_min is not None else None,
            salaryMax=float(obj.salary_max) if obj.salary_max is not None else None,
            salaryCurrency=obj.salary_currency,
            url=obj.url,
            postedAt=obj.posted_at,
            closingAt=obj.closing_at,
            isActive=obj.is_active,
            employerId=obj.employer_id,
            employerName=obj.employer.name if obj.employer else "",
            categoryId=obj.category_id,
            categoryName=obj.category.name if obj.category else None,
            sourceSlug=obj.source.slug if obj.source else "",
        )


class PostingHistoryOut(BaseModel):
    id: int
    changedAt: datetime
    fieldChanged: str
    oldValue: str | None = None
    newValue: str | None = None

    @classmethod
    def from_orm_obj(cls, obj):
        return cls(
            id=obj.id,
            changedAt=obj.changed_at,
            fieldChanged=obj.field_changed,
            oldValue=obj.old_value,
            newValue=obj.new_value,
        )
