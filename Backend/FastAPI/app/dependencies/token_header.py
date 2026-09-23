from typing import Annotated
from fastapi import Header, HTTPException

from ..config.settings import settings


async def get_token_header(x_token: Annotated[str, Header()]):
    expected_token = settings.API_KEY
    if x_token != expected_token:
        raise HTTPException(status_code=400, detail="X-Token header invalid")
