from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Simple health check endpoint to verify the server is running.
    Returns:
        JSONResponse: A JSON object indicating the server status.
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "message": "Server is working"}
    )
