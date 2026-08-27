package com.finassist.backend.dto;

import com.finassist.backend.entity.DocumentStatus;

import java.time.LocalDateTime;
import java.util.List;

public class ChatResponse {
    private Long id;
    private String title;
    private LocalDateTime createdAt;
    private List<DocumentSummaryDto> documents;

    public record DocumentSummaryDto(
            Long id,
            String fileName,
            String fileType,
            String documentType,
            DocumentStatus status,
            LocalDateTime uploadedAt,
            boolean isDeleted
    ) {}

    public ChatResponse(Long id, String title, LocalDateTime createdAt, List<DocumentSummaryDto> documents) {
        this.id = id;
        this.title = title;
        this.createdAt = createdAt;
        this.documents = documents;
    }

    public Long getId() { return id; }
    public String getTitle() { return title; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public List<DocumentSummaryDto> getDocuments() { return documents; }
}
