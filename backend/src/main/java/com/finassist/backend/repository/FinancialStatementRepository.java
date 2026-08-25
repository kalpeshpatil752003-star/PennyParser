package com.finassist.backend.repository;

import com.finassist.backend.entity.FinancialStatement;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface FinancialStatementRepository extends JpaRepository<FinancialStatement, Long> {
    List<FinancialStatement> findByDocumentId(Long documentId);
    void deleteByDocumentId(Long documentId);
}
