from fastapi import APIRouter

router = APIRouter()


@router.get('/health')
def health():
    return {"status": "ok", "message": "SIH26001 Landslide Risk API is running"}
