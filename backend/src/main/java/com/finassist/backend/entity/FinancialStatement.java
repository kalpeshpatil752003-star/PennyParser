package com.finassist.backend.entity;

import jakarta.persistence.*;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "financial_statements")
public class FinancialStatement {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "document_id", nullable = false)
    private Document document;

    @Column(name = "statement_type", nullable = false)
    private String statementType; // INCOME, BALANCE, CASHFLOW

    @Column(name = "fiscal_year")
    private Integer fiscalYear;

    @Column(name = "period")
    private String period; // Q1, Q2, Q3, Q4, FY

    @OneToMany(mappedBy = "statement", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<FinancialMetric> metrics = new ArrayList<>();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Document getDocument() { return document; }
    public void setDocument(Document document) { this.document = document; }

    public String getStatementType() { return statementType; }
    public void setStatementType(String statementType) { this.statementType = statementType; }

    public Integer getFiscalYear() { return fiscalYear; }
    public void setFiscalYear(Integer fiscalYear) { this.fiscalYear = fiscalYear; }

    public String getPeriod() { return period; }
    public void setPeriod(String period) { this.period = period; }

    public List<FinancialMetric> getMetrics() { return metrics; }
    public void setMetrics(List<FinancialMetric> metrics) { this.metrics = metrics; }
}
