package com.finassist.backend.repository;

import com.finassist.backend.entity.Document;
import com.finassist.backend.entity.DocumentStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface DocumentRepository extends JpaRepository<Document, Long> {
    Page<Document> findByUploadedById(Long userId, Pageable pageable);
    Page<Document> findByCompanyId(Long companyId, Pageable pageable);
    long countByStatus(DocumentStatus status);
    Optional<Document> findByIdAndUploadedById(Long id, Long userId);
}
