package com.finassist.backend.dto;

import com.finassist.backend.entity.DocumentStatus;
import java.time.LocalDateTime;

public class DocumentResponse {
    private Long id;
    private String fileName;
    private String fileType;
    private String documentType;
    private DocumentStatus status;
    private LocalDateTime uploadedAt;

    public DocumentResponse(Long id, String fileName, String fileType,
                            String documentType, DocumentStatus status, LocalDateTime uploadedAt) {
        this.id = id;
        this.fileName = fileName;
        this.fileType = fileType;
        this.documentType = documentType;
        this.status = status;
        this.uploadedAt = uploadedAt;
    }
    public Long getId() { return id; }
    public String getFileName() { return fileName; }
    public String getFileType() { return fileType; }
    public String getDocumentType() { return documentType; }
    public DocumentStatus getStatus() { return status; }
    public LocalDateTime getUploadedAt() { return uploadedAt; }
}