import enum


class SeniorityLevel(str, enum.Enum):
    intern = "intern"
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    manager = "manager"


class EmploymentType(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"
    freelance = "freelance"


class WebhookEvent(str, enum.Enum):
    new_posting = "posting.new"
    posting_changed = "posting.changed"
    posting_closed = "posting.closed"
