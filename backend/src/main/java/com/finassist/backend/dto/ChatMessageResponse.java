package com.finassist.backend.dto;

import com.finassist.backend.entity.MessageRole;
import java.time.LocalDateTime;
import java.util.List;

public class ChatMessageResponse {
    private Long id;
    private MessageRole role;
    private String content;
    private List<CitationDto> citations;
    private LocalDateTime createdAt;

    public record CitationDto(Long documentId, Integer page) {}

    public ChatMessageResponse(Long id, MessageRole role, String content, List<CitationDto> citations, LocalDateTime createdAt) {
        this.id = id; this.role = role; this.content = content; this.citations = citations; this.createdAt = createdAt;
    }
    public Long getId() { return id; }
    public MessageRole getRole() { return role; }
    public String getContent() { return content; }
    public List<CitationDto> getCitations() { return citations; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}