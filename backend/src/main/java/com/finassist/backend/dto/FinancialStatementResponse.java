package com.finassist.backend.dto;

import java.util.List;

public record FinancialStatementResponse(
        Long id,
        Long documentId,
        String statementType,
        Integer fiscalYear,
        String period,
        List<FinancialMetricDto> metrics
) {
    public record FinancialMetricDto(
            Long id,
            String metricName,
            Double metricValue,
            String unit,
            Integer sourcePage
    ) {}
}
