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
        List<Map<String, Object>> periods = (List<Map<String, Object>>) body.get("periods");
        @SuppressWarnings("unchecked")
        Map<String, Object> auditMetadata = (Map<String, Object>) body.get("auditMetadata");
        String sourceScale = auditMetadata != null ? (String) auditMetadata.get("sourceScaleDisplay") : null;
        if (sourceScale == null && auditMetadata != null) {
            sourceScale = (String) auditMetadata.get("source_scale_display");
        }

        @SuppressWarnings("unchecked")
        Map<String, Map<String, Object>> lineItems = (Map<String, Map<String, Object>>) body.get("lineItems");
        @SuppressWarnings("unchecked")
        Map<String, Number> ratios = (Map<String, Number>) body.get("ratios");

        java.util.List<FinancialStatement> statementsToSave = new java.util.ArrayList<>();

        if (periods != null && !periods.isEmpty()) {
            // Period-keyed structure (Phase 1)
            FinancialStatement summaryStmt = null;
            java.util.Set<String> metaKeys = java.util.Set.of(
                    "period_key", "period_type", "fiscal_year", "quarter",
                    "label", "start_date", "end_date", "as_of_date"
            );

            for (int i = 0; i < periods.size(); i++) {
                Map<String, Object> pMap = periods.get(i);
                FinancialStatement pStmt = new FinancialStatement();
                pStmt.setDocument(document);
                pStmt.setStatementType("PERIOD_DATA");

                String pKey = (String) pMap.get("period_key");
                String pType = (String) pMap.get("period_type");
                String label = (String) pMap.get("label");
                pStmt.setPeriod(label != null ? label : (pKey != null ? pKey.replace("_", " ") : "Period " + (i + 1)));
                pStmt.setPeriodType(pType);
                pStmt.setStartDate((String) pMap.get("start_date"));
                pStmt.setEndDate((String) pMap.get("end_date"));
                pStmt.setAsOfDate((String) pMap.get("as_of_date"));
                pStmt.setSourceScale(sourceScale);

                Object fyObj = pMap.get("fiscal_year");
                if (fyObj instanceof Number fyNum) {
                    pStmt.setFiscalYear(fyNum.intValue());
                }

                for (Map.Entry<String, Object> mEntry : pMap.entrySet()) {
                    if (metaKeys.contains(mEntry.getKey())) continue;
                    if (mEntry.getValue() instanceof Map<?, ?> valMapRaw) {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> valMap = (Map<String, Object>) valMapRaw;
                        Number numVal = (Number) valMap.get("value");
                        if (numVal != null) {
                            FinancialMetric m = new FinancialMetric();
                            m.setStatement(pStmt);
                            m.setMetricName(mEntry.getKey());
                            m.setMetricValue(numVal.doubleValue());
                            m.setSource((String) valMap.get("source"));
                            Number conf = (Number) valMap.get("confidence");
                            if (conf != null) m.setConfidence(conf.doubleValue());
                            Number page = (Number) valMap.get("source_page");
                            if (page == null) page = (Number) valMap.get("page");
                            if (page != null) m.setSourcePage(page.intValue());

                            String mKey = mEntry.getKey();
                            if (mKey.startsWith("eps")) {
                                m.setUnit("PER_SHARE");
                            } else if (mKey.endsWith("_pct") || mKey.contains("ratio") || mKey.contains("margin")) {
                                m.setUnit("RATIO_OR_PCT");
                            } else {
                                m.setUnit("CURRENCY");
                            }
                            pStmt.getMetrics().add(m);
                        }
                    }
                }
                statementsToSave.add(pStmt);

                // Designate the first duration period (or first period) as summary baseline
                if (summaryStmt == null || ("duration".equalsIgnoreCase(pType) && !"duration".equalsIgnoreCase(summaryStmt.getPeriodType()))) {
                    summaryStmt = pStmt;
                }
            }

            // Create FINANCIAL_SUMMARY statement mirroring primary period
            if (summaryStmt != null) {
                FinancialStatement mainSummary = new FinancialStatement();
                mainSummary.setDocument(document);
                mainSummary.setStatementType("FINANCIAL_SUMMARY");
                mainSummary.setPeriod(summaryStmt.getPeriod());
                mainSummary.setPeriodType(summaryStmt.getPeriodType());
                mainSummary.setFiscalYear(summaryStmt.getFiscalYear());
                mainSummary.setStartDate(summaryStmt.getStartDate());
                mainSummary.setEndDate(summaryStmt.getEndDate());
                mainSummary.setAsOfDate(summaryStmt.getAsOfDate());
                mainSummary.setSourceScale(sourceScale);

                for (FinancialMetric baseM : summaryStmt.getMetrics()) {
                    FinancialMetric sm = new FinancialMetric();
                    sm.setStatement(mainSummary);
                    sm.setMetricName(baseM.getMetricName());
                    sm.setMetricValue(baseM.getMetricValue());
                    sm.setUnit(baseM.getUnit());
                    sm.setSourcePage(baseM.getSourcePage());
                    sm.setSource(baseM.getSource());
                    sm.setConfidence(baseM.getConfidence());
                    mainSummary.getMetrics().add(sm);
                }

                if (ratios != null) {
                    for (Map.Entry<String, Number> entry : ratios.entrySet()) {
                        if (entry.getValue() != null) {
                            FinancialMetric metric = new FinancialMetric();
                            metric.setStatement(mainSummary);
                            metric.setMetricName(entry.getKey());
                            metric.setMetricValue(entry.getValue().doubleValue());
                            metric.setUnit("RATIO_OR_PCT");
                            metric.setSource("derived");
                            metric.setConfidence(1.0);
                            mainSummary.getMetrics().add(metric);
                        }
                    }
                }
                statementsToSave.add(0, mainSummary);
            }
        } else if (lineItems != null && !lineItems.isEmpty()) {
            // Legacy metric-keyed fallback
            FinancialStatement summaryStmt = new FinancialStatement();
            summaryStmt.setDocument(document);
            summaryStmt.setStatementType("FINANCIAL_SUMMARY");
            summaryStmt.setPeriod("FY");
            summaryStmt.setSourceScale(sourceScale);

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
                    metric.setSource((String) details.get("source"));
                    Number conf = (Number) details.get("confidence");
                    if (conf != null) metric.setConfidence(conf.doubleValue());
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
                            pMetric.setSource((String) details.get("source"));
                            Number conf = (Number) details.get("confidence");
                            if (conf != null) pMetric.setConfidence(conf.doubleValue());

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
                        metric.setSource("derived");
                        metric.setConfidence(1.0);
                        summaryStmt.getMetrics().add(metric);
                    }
                }
            }
            statementsToSave.add(summaryStmt);

            // Period-specific statements
            for (Map.Entry<String, java.util.List<FinancialMetric>> pEntry : periodMetricsMap.entrySet()) {
                String periodName = pEntry.getKey();
                FinancialStatement periodStmt = new FinancialStatement();
                periodStmt.setDocument(document);
                periodStmt.setStatementType("PERIOD_DATA");
                periodStmt.setPeriod(periodName.replace("_", " "));
                periodStmt.setSourceScale(sourceScale);

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
        }

            // 3. Period comparisons (pre-computed by AI service)
            @SuppressWarnings("unchecked")
            Map<String, Map<String, Object>> periodComparisons = (Map<String, Map<String, Object>>) body.get("periodComparisons");
            if (periodComparisons != null && !periodComparisons.isEmpty()) {
                FinancialStatement compStmt = new FinancialStatement();
                compStmt.setDocument(document);
                compStmt.setStatementType("PERIOD_COMPARISON");
                compStmt.setPeriod("COMPARISON");

                for (Map.Entry<String, Map<String, Object>> cEntry : periodComparisons.entrySet()) {
                    String metricName = cEntry.getKey();
                    Map<String, Object> compData = cEntry.getValue();
                    Number pctChange = (Number) compData.get("pct_change");
                    Number currentValue = (Number) compData.get("current_value");
                    Number priorValue = (Number) compData.get("prior_value");
                    String currentPeriod = (String) compData.get("current_period");
                    String priorPeriod = (String) compData.get("prior_period");

                    if (currentValue != null) {
                        FinancialMetric curMetric = new FinancialMetric();
                        curMetric.setStatement(compStmt);
                        curMetric.setMetricName(metricName + "__current");
                        curMetric.setMetricValue(currentValue.doubleValue());
                        curMetric.setUnit("CURRENCY");
                        compStmt.getMetrics().add(curMetric);
                    }
                    if (priorValue != null) {
                        FinancialMetric priorMetric = new FinancialMetric();
                        priorMetric.setStatement(compStmt);
                        priorMetric.setMetricName(metricName + "__prior");
                        priorMetric.setMetricValue(priorValue.doubleValue());
                        priorMetric.setUnit("CURRENCY");
                        compStmt.getMetrics().add(priorMetric);
                    }
                    if (pctChange != null) {
                        FinancialMetric pctMetric = new FinancialMetric();
                        pctMetric.setStatement(compStmt);
                        pctMetric.setMetricName(metricName + "__pct_change");
                        pctMetric.setMetricValue(pctChange.doubleValue());
                        pctMetric.setUnit("RATIO_OR_PCT");
                        compStmt.getMetrics().add(pctMetric);
                    }
                }
                statementsToSave.add(compStmt);
            }

        if (!statementsToSave.isEmpty()) {
            statementRepository.saveAll(statementsToSave);
        }
        return ResponseEntity.noContent().build();
    }
}