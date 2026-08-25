from fastapi import FastAPI
from app.routers import process

from app.routers import process, debug
from app.routers import process, debug, query

app = FastAPI(title="AI Financial Assistant - AI Service")
app.include_router(debug.router, prefix="/internal/v1")
app.include_router(process.router, prefix="/internal/v1")
app.include_router(query.router, prefix="/internal/v1")