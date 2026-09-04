package com.finassist.backend.dto;

import java.util.List;

public record FinancialStatementResponse(
        Long id,
        Long documentId,
        String statementType,
        Integer fiscalYear,
        String period,
        String periodType,
        String asOfDate,
        String sourceScale,
        List<FinancialMetricDto> metrics
) {
    public FinancialStatementResponse(
            Long id,
            Long documentId,
            String statementType,
            Integer fiscalYear,
            String period,
            List<FinancialMetricDto> metrics
    ) {
        this(id, documentId, statementType, fiscalYear, period, null, null, null, metrics);
    }

    public record FinancialMetricDto(
            Long id,
            String metricName,
            Double metricValue,
            String unit,
            Integer sourcePage,
            String source,
            Double confidence
    ) {
        public FinancialMetricDto(
                Long id,
                String metricName,
                Double metricValue,
                String unit,
                Integer sourcePage
        ) {
            this(id, metricName, metricValue, unit, sourcePage, "extracted", 1.0);
        }
    }
}
