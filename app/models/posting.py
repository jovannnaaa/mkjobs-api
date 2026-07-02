from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import EmploymentType, SeniorityLevel
from app.models.base import Base, TimestampMixin


class Posting(Base, TimestampMixin):
    __tablename__ = "postings"

    id: Mapped[int] = mapped_column(primary_key=True)

    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)

    # Identity within the source portal, used for upsert/dedup against the origin
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    seniority: Mapped[SeniorityLevel | None] = mapped_column(nullable=True)
    employment_type: Mapped[EmploymentType | None] = mapped_column(nullable=True)

    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)

    url: Mapped[str] = mapped_column(String(1024), nullable=False)

    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Fingerprint of normalized (title, employer, location) used by the
    # deduplication engine to fuzzy-match postings across sources.
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Marks this posting as a duplicate of another (cross-source dedup)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("postings.id"), nullable=True
    )

    source: Mapped["Source"] = relationship()
    employer: Mapped["Employer"] = relationship(back_populates="postings")
    category: Mapped["Category | None"] = relationship(back_populates="postings")
    history: Mapped[list["PostingHistory"]] = relationship(
        back_populates="posting", order_by="PostingHistory.changed_at.desc()"
    )
