from fastapi import APIRouter, BackgroundTasks
from app.models.schemas import ProcessRequest, ProcessAccepted
from app.services.pipeline import run_pipeline

router = APIRouter()

@router.post("/process", response_model=ProcessAccepted)
async def process_document(request: ProcessRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline, request.documentId, request.filePath, request.fileType)
    return ProcessAccepted(accepted=True)