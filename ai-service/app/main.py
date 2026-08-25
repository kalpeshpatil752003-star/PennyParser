from fastapi import FastAPI, Depends
from app.core.security import verify_internal_token
from app.routers import process, debug, query, document

app = FastAPI(title="AI Financial Assistant - AI Service")

internal_dependencies = [Depends(verify_internal_token)]

app.include_router(debug.router, prefix="/internal/v1", dependencies=internal_dependencies)
app.include_router(process.router, prefix="/internal/v1", dependencies=internal_dependencies)
app.include_router(query.router, prefix="/internal/v1", dependencies=internal_dependencies)
app.include_router(document.router, prefix="/internal/v1", dependencies=internal_dependencies)