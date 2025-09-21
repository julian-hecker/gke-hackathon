from fastapi import APIRouter, Response

router = APIRouter(prefix="/health", tags=["Health Check"], redirect_slashes=False)


@router.get("/", status_code=200)
async def health_check():
    """Health check endpoint"""
    return Response(status_code=200)
