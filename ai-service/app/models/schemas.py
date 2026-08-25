from pydantic import BaseModel

class ProcessRequest(BaseModel):
    documentId: int
    filePath: str
    fileType: str

class ProcessAccepted(BaseModel):
    accepted: bool