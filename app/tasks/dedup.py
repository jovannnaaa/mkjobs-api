"""Fuzzy deduplication of postings across sources.

Postings are compared by normalized (title, employer, location) using
token-set similarity. A match above the threshold marks the newer posting
as a duplicate of the earliest known one, so it's excluded from the
default `/api/postings` listing but its history is still recorded.
"""
import hashlib
import re

from rapidfuzz import fuzz

SIMILARITY_THRESHOLD = 88


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"[^\w\s]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def content_hash(title: str, employer_name: str, location: str | None) -> str:
    key = f"{normalize_text(title)}|{normalize_text(employer_name)}|{normalize_text(location)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def similarity_score(a_title: str, a_employer: str, a_location: str | None,
                      b_title: str, b_employer: str, b_location: str | None) -> float:
    a_key = f"{normalize_text(a_title)} {normalize_text(a_employer)} {normalize_text(a_location)}"
    b_key = f"{normalize_text(b_title)} {normalize_text(b_employer)} {normalize_text(b_location)}"
    return fuzz.token_set_ratio(a_key, b_key)


def is_duplicate(a_title: str, a_employer: str, a_location: str | None,
                  b_title: str, b_employer: str, b_location: str | None) -> bool:
    return similarity_score(a_title, a_employer, a_location, b_title, b_employer, b_location) >= SIMILARITY_THRESHOLD
