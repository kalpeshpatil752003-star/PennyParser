package com.finassist.backend.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "message_citations")
public class MessageCitation {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "message_id", nullable = false)
    private ChatMessage message;

    @Column(name = "document_id", nullable = false)
    private Long documentId;

    @Column(name = "page_number")
    private Integer pageNumber;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public ChatMessage getMessage() { return message; }
    public void setMessage(ChatMessage message) { this.message = message; }
    public Long getDocumentId() { return documentId; }
    public void setDocumentId(Long documentId) { this.documentId = documentId; }
    public Integer getPageNumber() { return pageNumber; }
    public void setPageNumber(Integer pageNumber) { this.pageNumber = pageNumber; }
}