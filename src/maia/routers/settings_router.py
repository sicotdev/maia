from fastapi import APIRouter
from maia.settings import SETTINGS

router = APIRouter()


@router.get("")
async def get_settings_data():
    return SETTINGS
