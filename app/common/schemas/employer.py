from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmployerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    website: str | None = None
    location: str | None = None
    createdAt: datetime

    @classmethod
    def from_orm_aliased(cls, obj):
        return cls(
            id=obj.id,
            name=obj.name,
            website=obj.website,
            location=obj.location,
            createdAt=obj.created_at,
        )
