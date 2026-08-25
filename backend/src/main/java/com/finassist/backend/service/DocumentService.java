package com.finassist.backend.service;

import com.finassist.backend.client.PythonAiServiceClient;
import com.finassist.backend.dto.DocumentResponse;
import com.finassist.backend.entity.*;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.DocumentRepository;
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

    @Value("${file.upload-dir}")
    private String uploadDir;

    private final DocumentRepository documentRepository;

    private final PythonAiServiceClient aiServiceClient;

    public DocumentService(DocumentRepository documentRepository, PythonAiServiceClient aiServiceClient) {
        this.documentRepository = documentRepository;
        this.aiServiceClient = aiServiceClient;
    }

    public DocumentResponse upload(MultipartFile file, User uploader) {
        validate(file);

        String storedFileName = System.currentTimeMillis() + "_" + file.getOriginalFilename();
        Path targetPath = Paths.get(uploadDir).resolve(storedFileName);

        try {
            Files.createDirectories(targetPath.getParent());
            file.transferTo(targetPath);
        } catch (IOException e) {
            throw new ApiException("Failed to store file", HttpStatus.INTERNAL_SERVER_ERROR);
        }

        Document document = new Document();
        document.setUploadedBy(uploader);
        document.setFileName(file.getOriginalFilename());
        document.setStoredFileName(storedFileName);
        document.setFileType(resolveFileType(file.getContentType()));
        document.setFileSize(file.getSize());
        document.setStatus(DocumentStatus.UPLOADED);
        documentRepository.save(document);

        aiServiceClient.triggerProcessing(document.getId(), targetPath.toAbsolutePath().normalize().toString(), document.getFileType());

        return toResponse(document);
    }

    public List<DocumentResponse> listForUser(Long userId) {
        return documentRepository.findByUploadedById(userId, org.springframework.data.domain.Pageable.unpaged())
                .stream().map(this::toResponse).toList();
    }

    public String getStatus(Long documentId) {
        Document doc = documentRepository.findById(documentId)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));
        return doc.getStatus().name();
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

    public void delete(Long documentId, Long userId) {

        Document document = documentRepository
                .findByIdAndUploadedById(documentId, userId)
                .orElseThrow(() -> new ApiException(
                        "Document not found",
                        HttpStatus.NOT_FOUND));

        Path filePath = Paths.get(uploadDir)
                .resolve(document.getStoredFileName());

        try {
            Files.deleteIfExists(filePath);
        } catch (IOException e) {
            throw new ApiException(
                    "Failed to delete file",
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }

        aiServiceClient.deleteDocumentVectors(documentId);
        documentRepository.delete(document);
    }
}