from fastapi import APIRouter, Response

router = APIRouter(prefix="/health", tags=["Health Check"])


@router.get("/", status_code=204)
async def health_check():
    """Health check endpoint"""
    return Response(status_code=204)
