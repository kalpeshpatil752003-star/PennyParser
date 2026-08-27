package com.finassist.backend.controller;

import com.finassist.backend.entity.*;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.*;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/internal/v1")
public class InternalDocumentController {

    private final DocumentRepository documentRepository;
    private final DocumentChunkRepository chunkRepository;
    private final FinancialStatementRepository statementRepository;

    public InternalDocumentController(DocumentRepository documentRepository,
                                      DocumentChunkRepository chunkRepository,
                                      FinancialStatementRepository statementRepository) {
        this.documentRepository = documentRepository;
        this.chunkRepository = chunkRepository;
        this.statementRepository = statementRepository;
    }

    @PutMapping("/documents/{id}/status")
    public ResponseEntity<Void> updateStatus(@PathVariable Long id,
                                             @RequestBody Map<String, String> body) {
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));

        String rawStatus = body.get("status");
        if (rawStatus == null) {
            throw new ApiException("Status string required", HttpStatus.BAD_REQUEST);
        }

        try {
            document.setStatus(DocumentStatus.valueOf(rawStatus.toUpperCase()));
            documentRepository.save(document);
        } catch (IllegalArgumentException e) {
            throw new ApiException("Invalid document status: " + rawStatus, HttpStatus.BAD_REQUEST);
        }
        return ResponseEntity.noContent().build();
    }

    public record ChunkSyncDto(Integer chunkIndex, Integer pageNumber, String textPreview, Integer vectorId) {}

    @PostMapping("/documents/{id}/chunks")
    @Transactional
    public ResponseEntity<Void> syncChunks(@PathVariable Long id,
                                           @RequestBody List<ChunkSyncDto> dtos) {
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));

        // Idempotency: delete previous chunks for this document
        chunkRepository.deleteByDocumentId(id);

        if (dtos != null && !dtos.isEmpty()) {
            List<DocumentChunk> chunks = dtos.stream().map(dto -> {
                DocumentChunk chunk = new DocumentChunk();
                chunk.setDocument(document);
                chunk.setChunkIndex(dto.chunkIndex());
                chunk.setPageNumber(dto.pageNumber());
                String preview = dto.textPreview();
                if (preview != null && preview.length() > 950) {
                    preview = preview.substring(0, 950);
                }
                chunk.setTextPreview(preview);
                chunk.setVectorId(dto.vectorId());
                return chunk;
            }).toList();
            chunkRepository.saveAll(chunks);
        }
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/documents/{id}/financials")
    @Transactional
    public ResponseEntity<Void> syncFinancials(@PathVariable Long id,
                                               @RequestBody Map<String, Object> body) {
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ApiException("Document not found", HttpStatus.NOT_FOUND));

        // Idempotency: delete previous statements for this document
        statementRepository.deleteByDocumentId(id);

        @SuppressWarnings("unchecked")
        Map<String, Map<String, Object>> lineItems = (Map<String, Map<String, Object>>) body.get("lineItems");
        @SuppressWarnings("unchecked")
        Map<String, Number> ratios = (Map<String, Number>) body.get("ratios");

        if (lineItems != null && !lineItems.isEmpty()) {
            java.util.List<FinancialStatement> statementsToSave = new java.util.ArrayList<>();

            // 1. Primary summary statement
            FinancialStatement summaryStmt = new FinancialStatement();
            summaryStmt.setDocument(document);
            summaryStmt.setStatementType("FINANCIAL_SUMMARY");
            summaryStmt.setPeriod("FY");

            // Map to collect metrics per period: period -> List<FinancialMetric>
            java.util.Map<String, java.util.List<FinancialMetric>> periodMetricsMap = new java.util.HashMap<>();

            for (Map.Entry<String, Map<String, Object>> entry : lineItems.entrySet()) {
                String metricName = entry.getKey();
                Map<String, Object> details = entry.getValue();
                Number val = (Number) details.get("value");
                Number page = (Number) details.get("page");

                if (val != null) {
                    FinancialMetric metric = new FinancialMetric();
                    metric.setStatement(summaryStmt);
                    metric.setMetricName(metricName);
                    metric.setMetricValue(val.doubleValue());
                    metric.setUnit("CURRENCY");
                    metric.setSourcePage(page != null ? page.intValue() : null);
                    summaryStmt.getMetrics().add(metric);
                }

                @SuppressWarnings("unchecked")
                Map<String, Object> byPeriod = (Map<String, Object>) details.get("by_period");
                if (byPeriod != null) {
                    for (Map.Entry<String, Object> pEntry : byPeriod.entrySet()) {
                        String periodName = pEntry.getKey();
                        Object pValObj = pEntry.getValue();
                        if (pValObj instanceof Number pVal) {
                            FinancialMetric pMetric = new FinancialMetric();
                            pMetric.setMetricName(metricName);
                            pMetric.setMetricValue(pVal.doubleValue());
                            pMetric.setUnit("CURRENCY");
                            pMetric.setSourcePage(page != null ? page.intValue() : null);

                            periodMetricsMap.computeIfAbsent(periodName, k -> new java.util.ArrayList<>()).add(pMetric);
                        }
                    }
                }
            }

            if (ratios != null) {
                for (Map.Entry<String, Number> entry : ratios.entrySet()) {
                    if (entry.getValue() != null) {
                        FinancialMetric metric = new FinancialMetric();
                        metric.setStatement(summaryStmt);
                        metric.setMetricName(entry.getKey());
                        metric.setMetricValue(entry.getValue().doubleValue());
                        metric.setUnit("RATIO_OR_PCT");
                        summaryStmt.getMetrics().add(metric);
                    }
                }
            }
            statementsToSave.add(summaryStmt);

            // 2. Period-specific statements
            for (Map.Entry<String, java.util.List<FinancialMetric>> pEntry : periodMetricsMap.entrySet()) {
                String periodName = pEntry.getKey();
                FinancialStatement periodStmt = new FinancialStatement();
                periodStmt.setDocument(document);
                periodStmt.setStatementType("PERIOD_DATA");
                periodStmt.setPeriod(periodName.replace("_", " "));

                // Extract potential fiscal year from period name (e.g. "Q2 2026" -> 2026)
                java.util.regex.Matcher m = java.util.regex.Pattern.compile("\\b(19\\d\\d|20\\d\\d)\\b").matcher(periodName);
                if (m.find()) {
                    try {
                        periodStmt.setFiscalYear(Integer.parseInt(m.group(1)));
                    } catch (NumberFormatException ignored) {}
                }

                for (FinancialMetric mMetric : pEntry.getValue()) {
                    mMetric.setStatement(periodStmt);
                    periodStmt.getMetrics().add(mMetric);
                }
                statementsToSave.add(periodStmt);
            }

            statementRepository.saveAll(statementsToSave);
        }
        return ResponseEntity.noContent().build();
    }
}