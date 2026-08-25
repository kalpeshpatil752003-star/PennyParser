package com.finassist.backend.service;

import com.finassist.backend.client.PythonAiServiceClient;
import com.finassist.backend.dto.DocumentResponse;
import com.finassist.backend.entity.Document;
import com.finassist.backend.entity.DocumentStatus;
import com.finassist.backend.entity.User;
import com.finassist.backend.exception.ApiException;
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
    private PythonAiServiceClient aiServiceClient;
    private DocumentService documentService;

    private User userA;
    private User userB;

    @BeforeEach
    void setUp() {
        documentRepository = mock(DocumentRepository.class);
        statementRepository = mock(FinancialStatementRepository.class);
        aiServiceClient = mock(PythonAiServiceClient.class);
        documentService = new DocumentService(documentRepository, statementRepository, aiServiceClient);

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

        when(documentRepository.findByIdAndUploadedById(10L, 1L)).thenReturn(Optional.of(doc));

        String status = documentService.getStatus(10L, 1L);
        assertEquals("READY", status);
    }

    @Test
    void getStatus_otherUserDocument_throwsNotFound() {
        when(documentRepository.findByIdAndUploadedById(10L, 2L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> documentService.getStatus(10L, 2L));
        assertEquals("Document not found", ex.getMessage());
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
        // Ensure original filename was sanitized from path traversal
        assertEquals("passwd.pdf", response.getFileName());
        verify(aiServiceClient).triggerProcessing(eq(50L), anyString(), eq("PDF"));
    }
}
