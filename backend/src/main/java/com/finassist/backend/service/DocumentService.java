package com.finassist.backend.service;

import com.finassist.backend.client.PythonAiServiceClient;
import com.finassist.backend.dto.DocumentResponse;
import com.finassist.backend.entity.*;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.DocumentRepository;
import com.finassist.backend.repository.FinancialStatementRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.*;
import java.util.List;
import java.util.Set;

@Service
public class DocumentService {

    private static final Set<String> ALLOWED_TYPES = Set.of(
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
    );

    @Value("${file.upload-dir:uploads}")
    private String uploadDir = "uploads";

    private final DocumentRepository documentRepository;
    private final FinancialStatementRepository statementRepository;
    private final com.finassist.backend.repository.DocumentChunkRepository chunkRepository;
    private final PythonAiServiceClient aiServiceClient;

    public DocumentService(DocumentRepository documentRepository,
                           FinancialStatementRepository statementRepository,
                           com.finassist.backend.repository.DocumentChunkRepository chunkRepository,
                           PythonAiServiceClient aiServiceClient) {
        this.documentRepository = documentRepository;
        this.statementRepository = statementRepository;
        this.chunkRepository = chunkRepository;
        this.aiServiceClient = aiServiceClient;
    }

    public DocumentResponse upload(MultipartFile file, User uploader) {
        validate(file);

        String rawFilename = file.getOriginalFilename();
        String sanitizedFilename = rawFilename != null ? Paths.get(rawFilename).getFileName().toString() : "upload.bin";
        String storedFileName = java.util.UUID.randomUUID() + "_" + sanitizedFilename;

        Path baseDirPath = Paths.get(uploadDir).toAbsolutePath().normalize();
        Path targetPath = baseDirPath.resolve(storedFileName).normalize();

        if (!targetPath.startsWith(baseDirPath)) {
            throw new ApiException("Invalid upload filename", HttpStatus.BAD_REQUEST);
        }

        try {
            Files.createDirectories(targetPath.getParent());
            file.transferTo(targetPath);
        } catch (IOException e) {
            throw new ApiException("Failed to store file", HttpStatus.INTERNAL_SERVER_ERROR);
        }

        Document document = new Document();
        document.setUploadedBy(uploader);
        document.setFileName(sanitizedFilename);
        document.setStoredFileName(storedFileName);
        document.setFileType(resolveFileType(file.getContentType()));
        document.setFileSize(file.getSize());
        document.setStatus(DocumentStatus.UPLOADED);
        documentRepository.save(document);

        aiServiceClient.triggerProcessing(document.getId(), targetPath.toAbsolutePath().normalize().toString(), document.getFileType());

        return toResponse(document);
    }

    public List<DocumentResponse> listForUser(Long userId) {
        return documentRepository.findByUploadedByIdAndDeletedAtIsNull(userId, org.springframework.data.domain.Pageable.unpaged())
                .stream().map(this::toResponse).toList();
    }

    public DocumentResponse getDocument(Long documentId, Long userId) {
        Document doc = documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(documentId, userId)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));
        return toResponse(doc);
    }

    public String getStatus(Long documentId, Long userId) {
        Document doc = documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(documentId, userId)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));
        return doc.getStatus().name();
    }

    public List<com.finassist.backend.dto.FinancialStatementResponse> getFinancialStatements(Long documentId, Long userId) {
        Document doc = documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(documentId, userId)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));

        List<FinancialStatement> statements = statementRepository.findByDocumentId(doc.getId());
        return statements.stream().map(stmt -> new com.finassist.backend.dto.FinancialStatementResponse(
                stmt.getId(),
                doc.getId(),
                stmt.getStatementType(),
                stmt.getFiscalYear(),
                stmt.getPeriod(),
                stmt.getMetrics().stream().map(m -> new com.finassist.backend.dto.FinancialStatementResponse.FinancialMetricDto(
                        m.getId(), m.getMetricName(), m.getMetricValue(), m.getUnit(), m.getSourcePage()
                )).toList()
        )).toList();
    }

    private void validate(MultipartFile file) {
        if (file.isEmpty()) {
            throw new ApiException("File is empty", HttpStatus.BAD_REQUEST);
        }
        if (!ALLOWED_TYPES.contains(file.getContentType())) {
            throw new ApiException("Unsupported file type: " + file.getContentType(), HttpStatus.BAD_REQUEST);
        }
    }

    private String resolveFileType(String contentType) {
        if (contentType == null) return "UNKNOWN";
        if (contentType.contains("pdf")) return "PDF";
        if (contentType.contains("wordprocessingml")) return "DOCX";
        return "TXT";
    }

    private DocumentResponse toResponse(Document d) {
        return new DocumentResponse(d.getId(), d.getFileName(), d.getFileType(),
                d.getDocumentType(), d.getStatus(), d.getUploadedAt());
    }

    @org.springframework.transaction.annotation.Transactional
    public void delete(Long documentId, Long userId) {
        // 1. Authenticate ownership + active document lookup (throws 404 if not found or already deleted)
        Document document = documentRepository
                .findByIdAndUploadedByIdAndDeletedAtIsNull(documentId, userId)
                .orElseThrow(() -> new ApiException(
                        "Document not found",
                        HttpStatus.NOT_FOUND));

        // 2. Mark document as soft-deleted in PostgreSQL
        document.setDeletedAt(java.time.LocalDateTime.now());
        document.setStatus(DocumentStatus.FAILED);
        documentRepository.save(document);

        // 3. Clean up database dependencies within current transaction
        chunkRepository.deleteByDocumentId(documentId);
        statementRepository.deleteByDocumentId(documentId);

        // 4. Idempotent external cleanups (outside ACID transaction)
        // Vector cleanup in Python AI Service
        try {
            aiServiceClient.deleteDocumentVectors(documentId);
        } catch (Exception e) {
            System.err.println("Warning: failed to delete vectors from AI service: " + e.getMessage());
        }

        // Physical file cleanup (safe path inside uploadDir)
        if (document.getStoredFileName() != null) {
            Path baseDirPath = Paths.get(uploadDir).toAbsolutePath().normalize();
            Path filePath = baseDirPath.resolve(document.getStoredFileName()).normalize();
            if (filePath.startsWith(baseDirPath)) {
                try {
                    Files.deleteIfExists(filePath);
                } catch (IOException e) {
                    System.err.println("Warning: failed to delete physical file: " + e.getMessage());
                }
            }
        }
    }
}