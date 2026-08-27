package com.finassist.backend.service;

import com.finassist.backend.client.PythonAiServiceClient;
import com.finassist.backend.dto.DocumentResponse;
import com.finassist.backend.entity.Document;
import com.finassist.backend.entity.DocumentStatus;
import com.finassist.backend.entity.User;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.DocumentChunkRepository;
import com.finassist.backend.repository.DocumentRepository;
import com.finassist.backend.repository.FinancialStatementRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class DocumentServiceTest {

    private DocumentRepository documentRepository;
    private FinancialStatementRepository statementRepository;
    private DocumentChunkRepository chunkRepository;
    private PythonAiServiceClient aiServiceClient;
    private DocumentService documentService;

    private User userA;
    private User userB;

    @BeforeEach
    void setUp() {
        documentRepository = mock(DocumentRepository.class);
        statementRepository = mock(FinancialStatementRepository.class);
        chunkRepository = mock(DocumentChunkRepository.class);
        aiServiceClient = mock(PythonAiServiceClient.class);
        documentService = new DocumentService(documentRepository, statementRepository, chunkRepository, aiServiceClient);

        userA = new User();
        userA.setId(1L);
        userA.setEmail("usera@example.com");

        userB = new User();
        userB.setId(2L);
        userB.setEmail("userb@example.com");
    }

    @Test
    void getStatus_belongingToUser_success() {
        Document doc = new Document();
        doc.setId(10L);
        doc.setStatus(DocumentStatus.READY);

        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 1L)).thenReturn(Optional.of(doc));

        String status = documentService.getStatus(10L, 1L);
        assertEquals("READY", status);
    }

    @Test
    void getStatus_otherUserDocument_throwsNotFound() {
        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 2L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> documentService.getStatus(10L, 2L));
        assertEquals("Document not found", ex.getMessage());
    }

    @Test
    void listForUser_excludesDeletedDocuments() {
        Document docActive = new Document();
        docActive.setId(10L);
        docActive.setFileName("active.pdf");
        docActive.setFileType("PDF");
        docActive.setStatus(DocumentStatus.READY);

        when(documentRepository.findByUploadedByIdAndDeletedAtIsNull(eq(1L), any()))
                .thenReturn(new org.springframework.data.domain.PageImpl<>(java.util.List.of(docActive)));

        var docs = documentService.listForUser(1L);
        assertEquals(1, docs.size());
        assertEquals(10L, docs.get(0).getId());
        assertEquals("active.pdf", docs.get(0).getFileName());
    }

    @Test
    void getDocument_deletedDocument_throwsNotFound() {
        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 1L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> documentService.getDocument(10L, 1L));
        assertEquals("Document not found", ex.getMessage());
    }

    @Test
    void delete_ownActiveDocument_softDeletesAndCleansDependencies() {
        Document doc = new Document();
        doc.setId(10L);
        doc.setStoredFileName("uuid_test.pdf");
        doc.setStatus(DocumentStatus.READY);

        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 1L)).thenReturn(Optional.of(doc));
        when(documentRepository.save(any(Document.class))).thenAnswer(inv -> inv.getArgument(0));

        documentService.delete(10L, 1L);

        // Verify: marked as deleted with timestamp
        assertNotNull(doc.getDeletedAt());
        assertEquals(DocumentStatus.FAILED, doc.getStatus());
        verify(documentRepository).save(doc);

        // Verify: database dependencies deleted
        verify(chunkRepository).deleteByDocumentId(10L);
        verify(statementRepository).deleteByDocumentId(10L);

        // Verify: AI service vectors cleaned up
        verify(aiServiceClient).deleteDocumentVectors(10L);
    }

    @Test
    void delete_otherUserDocument_throwsNotFound() {
        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 2L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> documentService.delete(10L, 2L));
        assertEquals("Document not found", ex.getMessage());
        verify(documentRepository, never()).save(any());
        verify(chunkRepository, never()).deleteByDocumentId(any());
        verify(aiServiceClient, never()).deleteDocumentVectors(any());
    }

    @Test
    void delete_alreadyDeletedDocument_throwsNotFound() {
        // Second deletion attempt of the same document returns 404
        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 1L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> documentService.delete(10L, 1L));
        assertEquals("Document not found", ex.getMessage());
        verify(documentRepository, never()).save(any());
    }

    @Test
    void upload_pathTraversalFilename_sanitizesFilename() {
        MockMultipartFile file = new MockMultipartFile("file", "../../etc/passwd.pdf", "application/pdf", "dummy pdf content".getBytes());

        when(documentRepository.save(any(Document.class))).thenAnswer(invocation -> {
            Document d = invocation.getArgument(0);
            d.setId(50L);
            return d;
        });

        DocumentResponse response = documentService.upload(file, userA);

        assertNotNull(response);
        assertEquals("passwd.pdf", response.getFileName());
        verify(aiServiceClient).triggerProcessing(eq(50L), anyString(), eq("PDF"));
    }

    @Test
    void getFinancialStatements_ownDocument_success() {
        Document doc = new Document();
        doc.setId(10L);

        com.finassist.backend.entity.FinancialStatement stmt = new com.finassist.backend.entity.FinancialStatement();
        stmt.setId(100L);
        stmt.setStatementType("FINANCIAL_SUMMARY");
        stmt.setPeriod("FY");

        com.finassist.backend.entity.FinancialMetric metric = new com.finassist.backend.entity.FinancialMetric();
        metric.setId(200L);
        metric.setMetricName("revenue");
        metric.setMetricValue(60801.0);
        metric.setUnit("CURRENCY");
        stmt.getMetrics().add(metric);

        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 1L)).thenReturn(Optional.of(doc));
        when(statementRepository.findByDocumentId(10L)).thenReturn(java.util.List.of(stmt));

        var result = documentService.getFinancialStatements(10L, 1L);
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("FINANCIAL_SUMMARY", result.get(0).statementType());
        assertEquals(1, result.get(0).metrics().size());
        assertEquals("revenue", result.get(0).metrics().get(0).metricName());
        assertEquals(60801.0, result.get(0).metrics().get(0).metricValue());
    }

    @Test
    void getFinancialStatements_otherUserDocument_throwsNotFound() {
        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 2L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> documentService.getFinancialStatements(10L, 2L));
        assertEquals("Document not found", ex.getMessage());
        verify(statementRepository, never()).findByDocumentId(any());
    }

    @Test
    void getFinancialStatements_deletedDocument_throwsNotFound() {
        when(documentRepository.findByIdAndUploadedByIdAndDeletedAtIsNull(10L, 1L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> documentService.getFinancialStatements(10L, 1L));
        assertEquals("Document not found", ex.getMessage());
        verify(statementRepository, never()).findByDocumentId(any());
    }
}
