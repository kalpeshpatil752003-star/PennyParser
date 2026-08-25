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
            FinancialStatement stmt = new FinancialStatement();
            stmt.setDocument(document);
            stmt.setStatementType("FINANCIAL_SUMMARY");
            stmt.setPeriod("FY");

            for (Map.Entry<String, Map<String, Object>> entry : lineItems.entrySet()) {
                String metricName = entry.getKey();
                Map<String, Object> details = entry.getValue();
                Number val = (Number) details.get("value");
                Number page = (Number) details.get("page");

                if (val != null) {
                    FinancialMetric metric = new FinancialMetric();
                    metric.setStatement(stmt);
                    metric.setMetricName(metricName);
                    metric.setMetricValue(val.doubleValue());
                    metric.setUnit("CURRENCY");
                    metric.setSourcePage(page != null ? page.intValue() : null);
                    stmt.getMetrics().add(metric);
                }
            }

            if (ratios != null) {
                for (Map.Entry<String, Number> entry : ratios.entrySet()) {
                    if (entry.getValue() != null) {
                        FinancialMetric metric = new FinancialMetric();
                        metric.setStatement(stmt);
                        metric.setMetricName(entry.getKey());
                        metric.setMetricValue(entry.getValue().doubleValue());
                        metric.setUnit("RATIO_OR_PCT");
                        stmt.getMetrics().add(metric);
                    }
                }
            }

            statementRepository.save(stmt);
        }
        return ResponseEntity.noContent().build();
    }
}