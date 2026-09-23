from sqlalchemy.orm import Session
from fastapi import APIRouter, File, Form, UploadFile, Query, HTTPException,Depends
from typing import List
from fastapi.responses import JSONResponse
from ..services import file_services
import logging


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Files"],
    responses={404: {"description": "Not found"}},
)

@router.post("/upload/hoodwinked")
async def upload_hoodwinked(
    files: List[UploadFile] = File(...),
    user_email: str = Form(...),
    platform: str = Form(...),
):
    """
    POST :- /api/analytics/upload/hoodwinked

    Endpoint to upload files.

    Form data:
        files (List[UploadFile]): List of files to be uploaded.
        user_email (str): User's email address.
        platform (str): Platform name.

    Returns:
        dict: Response message and uploaded file data.
    """
    try:
        return file_services.upload_file(files, user_email, platform)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


@router.post("/delete-file/hoodwinked")
async def delete_hoodwinked(file_path: str):
    """
    POST: /api/analytics/delete-file/hoodwinked
    Endpoint to delete a file from S3 based on its path.
    """
    try:
        return file_services.delete_file(file_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during file deletion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

