from fastapi import APIRouter

router = APIRouter(tags=["discovery"])


@router.get("/.well-known")
async def well_known():
    return {
        "name": "MkJobs API",
        "version": "1.0",
        "endpoints": {
            "ping": "/api/ping",
            "ready": "/api/ready",
            "reference": "/api/reference",
            "stats": "/api/stats",
            "postings": "/api/postings",
            "posting": "/api/postings/{id}",
            "postingHistory": "/api/postings/{id}/history",
            "employers": "/api/employers",
            "employer": "/api/employers/{id}",
            "employerPostings": "/api/employers/{id}/postings",
            "categories": "/api/categories",
            "categoryPostings": "/api/categories/{id}/postings",
        },
        "pagination": {"style": "cursor", "defaultPageSize": 10, "maxPageSize": 100},
    }
