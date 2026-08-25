package com.finassist.backend.controller;

import com.finassist.backend.entity.DocumentStatus;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.DocumentRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/internal/v1")
public class InternalDocumentController {

    private final DocumentRepository documentRepository;

    @Value("${internal.service-token}")
    private String expectedToken;

    public InternalDocumentController(DocumentRepository documentRepository) {
        this.documentRepository = documentRepository;
    }

    @PutMapping("/documents/{id}/status")
    public ResponseEntity<Void> updateStatus(@PathVariable Long id,
                                             @RequestBody Map<String, String> body,
                                             @RequestHeader("X-Internal-Token") String token) {
        if (!expectedToken.equals(token)) {
            throw new ApiException("Invalid internal token", HttpStatus.FORBIDDEN);
        }
        var document = documentRepository.findById(id)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));
        document.setStatus(DocumentStatus.valueOf(body.get("status")));
        documentRepository.save(document);
        return ResponseEntity.noContent().build();
    }
}