package com.finassist.backend.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "financial_metrics")
public class FinancialMetric {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "statement_id", nullable = false)
    private FinancialStatement statement;

    @Column(name = "metric_name", nullable = false)
    private String metricName;

    @Column(name = "metric_value")
    private Double metricValue;

    @Column(name = "unit")
    private String unit;

    @Column(name = "source_page")
    private Integer sourcePage;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public FinancialStatement getStatement() { return statement; }
    public void setStatement(FinancialStatement statement) { this.statement = statement; }

    public String getMetricName() { return metricName; }
    public void setMetricName(String metricName) { this.metricName = metricName; }

    public Double getMetricValue() { return metricValue; }
    public void setMetricValue(Double metricValue) { this.metricValue = metricValue; }

    public String getUnit() { return unit; }
    public void setUnit(String unit) { this.unit = unit; }

    public Integer getSourcePage() { return sourcePage; }
    public void setSourcePage(Integer sourcePage) { this.sourcePage = sourcePage; }
}
