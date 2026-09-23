import pkgutil
import logging
from app.utils.logging_dd import DatadogHandler

# Temporary fix for Python 3.12 compatibility
if not hasattr(pkgutil, "ImpImporter"):
    pkgutil.ImpImporter = pkgutil.zipimporter

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.dependencies.auth import docs_authenticate
from .routers import (
    file_routes,
    graph_routes,
    recommendation_routes,
    report_routes,
    s3_routes,
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(s3_routes.router)
app.include_router(report_routes.router)
app.include_router(recommendation_routes.router)
app.include_router(file_routes.router)
app.include_router(graph_routes.router)

uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.addHandler(DatadogHandler())

@app.get("/docs", include_in_schema=False)
async def swagger_ui(
    credentials: HTTPBasicCredentials = Depends(docs_authenticate),
):
    return get_swagger_ui_html(
        openapi_url="/openapi.json", title="Hoodwinked Swagger UI"
    )


@app.get("/openapi.json", include_in_schema=False)
async def openapi(credentials: HTTPBasicCredentials = Depends(docs_authenticate)):
    return get_openapi(title="Hoodwinked API", version="1.0.0", routes=app.routes)


@app.get("/")
async def root():
    return {"message": "Hello Hoodwinked!"}
