package com.finassist.backend.controller;

import com.finassist.backend.dto.DocumentResponse;
import com.finassist.backend.entity.User;
import com.finassist.backend.service.DocumentService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/documents")
public class DocumentController {

    private final DocumentService documentService;

    public DocumentController(DocumentService documentService) {
        this.documentService = documentService;
    }

    @PostMapping(consumes = "multipart/form-data")
    public ResponseEntity<DocumentResponse> upload(
            @RequestParam("file") MultipartFile file,
            @AuthenticationPrincipal User user) {

        return ResponseEntity
                .status(HttpStatus.CREATED)
                .body(documentService.upload(file, user));
    }

    @GetMapping
    public ResponseEntity<List<DocumentResponse>> list(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(documentService.listForUser(user.getId()));
    }

    @GetMapping("/{id}/status")
    public ResponseEntity<Map<String, String>> status(@PathVariable Long id) {
        return ResponseEntity.ok(Map.of("status", documentService.getStatus(id)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable Long id,
            @AuthenticationPrincipal User user) {

        documentService.delete(id, user.getId());
        return ResponseEntity.noContent().build();
    }
}