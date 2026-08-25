package com.finassist.backend.repository;

import com.finassist.backend.entity.FinancialMetric;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface FinancialMetricRepository extends JpaRepository<FinancialMetric, Long> {
    List<FinancialMetric> findByStatementId(Long statementId);
}
