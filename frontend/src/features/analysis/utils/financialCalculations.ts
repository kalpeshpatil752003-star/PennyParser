import type { FinancialStatement } from '../../../types';

export interface ParsedFinancialData {
  primaryMetrics: Record<string, number>;
  ratios: Record<string, number>;
  periods: string[];
  periodMetrics: Record<string, Record<string, number>>; // periodName -> { metricName -> value }
  sourcePages: Record<string, number>;
  hasData: boolean;
}

export interface MetricComparison {
  metricKey: string;
  label: string;
  category: 'INCOME' | 'BALANCE' | 'RATIO' | 'OTHER';
  currentVal: number | null;
  previousVal: number | null;
  absoluteChange: number | null;
  percentChange: number | null;
  trend: 'up' | 'down' | 'neutral';
}

export const METRIC_LABELS: Record<string, { label: string; category: 'INCOME' | 'BALANCE' | 'RATIO' | 'OTHER' }> = {
  revenue: { label: 'Revenue', category: 'INCOME' },
  cost_of_goods_sold: { label: 'Cost of Revenue', category: 'INCOME' },
  gross_profit: { label: 'Gross Profit', category: 'INCOME' },
  operating_income: { label: 'Operating Income', category: 'INCOME' },
  net_income: { label: 'Net Income', category: 'INCOME' },
  eps_basic: { label: 'Basic Earnings Per Share (EPS)', category: 'INCOME' },
  eps_diluted: { label: 'Diluted Earnings Per Share (EPS)', category: 'INCOME' },
  total_assets: { label: 'Total Assets', category: 'BALANCE' },
  total_liabilities: { label: 'Total Liabilities', category: 'BALANCE' },
  total_equity: { label: "Stockholders' Equity", category: 'BALANCE' },
  current_assets: { label: 'Current Assets', category: 'BALANCE' },
  current_liabilities: { label: 'Current Liabilities', category: 'BALANCE' },
  current_ratio: { label: 'Current Ratio', category: 'RATIO' },
  debt_to_equity: { label: 'Debt to Equity', category: 'RATIO' },
  gross_margin_pct: { label: 'Gross Margin', category: 'RATIO' },
  operating_margin_pct: { label: 'Operating Margin', category: 'RATIO' },
  net_margin_pct: { label: 'Net Margin', category: 'RATIO' },
  roa_pct: { label: 'Return on Assets (ROA)', category: 'RATIO' },
  roe_pct: { label: 'Return on Equity (ROE)', category: 'RATIO' },
};

/**
 * Parses raw FinancialStatement[] from the backend into a structured, easily queryable format.
 */
export function parseFinancialStatements(statements: FinancialStatement[]): ParsedFinancialData {
  const primaryMetrics: Record<string, number> = {};
  const ratios: Record<string, number> = {};
  const periodMetrics: Record<string, Record<string, number>> = {};
  const sourcePages: Record<string, number> = {};
  const periodSet = new Set<string>();

  if (!Array.isArray(statements) || statements.length === 0) {
    return {
      primaryMetrics: {},
      ratios: {},
      periods: [],
      periodMetrics: {},
      sourcePages: {},
      hasData: false,
    };
  }

  for (const stmt of statements) {
    const period = stmt.period || 'FY';

    if (stmt.statementType === 'FINANCIAL_SUMMARY') {
      for (const m of stmt.metrics) {
        if (m.unit === 'RATIO_OR_PCT' || m.metricName.includes('pct') || m.metricName.includes('ratio') || m.metricName.includes('debt_to_equity')) {
          ratios[m.metricName] = m.metricValue;
        } else {
          primaryMetrics[m.metricName] = m.metricValue;
        }
        if (m.sourcePage != null) {
          sourcePages[m.metricName] = m.sourcePage;
        }
      }
    } else if (stmt.statementType === 'PERIOD_DATA' || period !== 'FY') {
      periodSet.add(period);
      if (!periodMetrics[period]) {
        periodMetrics[period] = {};
      }
      for (const m of stmt.metrics) {
        periodMetrics[period][m.metricName] = m.metricValue;
        if (!primaryMetrics[m.metricName]) {
          primaryMetrics[m.metricName] = m.metricValue;
        }
        if (m.sourcePage != null && !sourcePages[m.metricName]) {
          sourcePages[m.metricName] = m.sourcePage;
        }
      }
    } else {
      // General statement
      for (const m of stmt.metrics) {
        if (!primaryMetrics[m.metricName]) {
          primaryMetrics[m.metricName] = m.metricValue;
        }
        if (m.sourcePage != null) {
          sourcePages[m.metricName] = m.sourcePage;
        }
      }
    }
  }

  // Derive any missing ratios deterministically if underlying metrics exist
  const rev = primaryMetrics['revenue'];
  const cogs = primaryMetrics['cost_of_goods_sold'];
  const gp = primaryMetrics['gross_profit'] ?? (rev && cogs ? rev - cogs : undefined);
  const opInc = primaryMetrics['operating_income'];
  const netInc = primaryMetrics['net_income'];
  const totAssets = primaryMetrics['total_assets'];
  const totLiab = primaryMetrics['total_liabilities'];
  const totEquity = primaryMetrics['total_equity'];
  const curAssets = primaryMetrics['current_assets'];
  const curLiab = primaryMetrics['current_liabilities'];

  if (ratios['gross_margin_pct'] == null && rev && gp != null) {
    ratios['gross_margin_pct'] = Number(((gp / rev) * 100).toFixed(2));
  }
  if (ratios['operating_margin_pct'] == null && rev && opInc != null) {
    ratios['operating_margin_pct'] = Number(((opInc / rev) * 100).toFixed(2));
  }
  if (ratios['net_margin_pct'] == null && rev && netInc != null) {
    ratios['net_margin_pct'] = Number(((netInc / rev) * 100).toFixed(2));
  }
  if (ratios['roe_pct'] == null && totEquity && netInc != null) {
    ratios['roe_pct'] = Number(((netInc / totEquity) * 100).toFixed(2));
  }
  if (ratios['roa_pct'] == null && totAssets && netInc != null) {
    ratios['roa_pct'] = Number(((netInc / totAssets) * 100).toFixed(2));
  }
  if (ratios['debt_to_equity'] == null && totEquity && totLiab != null) {
    ratios['debt_to_equity'] = Number((totLiab / totEquity).toFixed(2));
  }
  if (ratios['current_ratio'] == null && curLiab && curAssets != null) {
    ratios['current_ratio'] = Number((curAssets / curLiab).toFixed(2));
  }

  // Sort periods logically (e.g. newer period first, or chronological)
  const periods = Array.from(periodSet).sort((a, b) => {
    return b.localeCompare(a, undefined, { numeric: true, sensitivity: 'base' });
  });

  const hasData = Object.keys(primaryMetrics).length > 0 || Object.keys(ratios).length > 0;

  return {
    primaryMetrics,
    ratios,
    periods,
    periodMetrics,
    sourcePages,
    hasData,
  };
}

/**
 * Calculates absolute and percentage change between current and previous values.
 * Formula: ((current - previous) / |previous|) * 100
 */
export function calculateDelta(
  current: number | null | undefined,
  previous: number | null | undefined
): { absoluteChange: number | null; percentChange: number | null; trend: 'up' | 'down' | 'neutral' } {
  if (current == null || previous == null || isNaN(current) || isNaN(previous)) {
    return { absoluteChange: null, percentChange: null, trend: 'neutral' };
  }

  const absoluteChange = Number((current - previous).toFixed(2));
  if (previous === 0) {
    return { absoluteChange, percentChange: null, trend: absoluteChange > 0 ? 'up' : absoluteChange < 0 ? 'down' : 'neutral' };
  }

  const percentChange = Number((((current - previous) / Math.abs(previous)) * 100).toFixed(1));
  const trend: 'up' | 'down' | 'neutral' =
    percentChange > 0 ? 'up' : percentChange < 0 ? 'down' : 'neutral';

  return { absoluteChange, percentChange, trend };
}

/**
 * Format currency number with magnitude-aware abbreviation.
 * Dynamically picks unit label (K/M/B/T) based on actual value size.
 * Works for any company at any scale — small-cap in thousands and mega-cap in billions.
 */
export function formatCurrency(
  val: number | null | undefined,
  options: { showSymbol?: boolean; suffix?: string } = {}
): string {
  if (val == null || isNaN(val)) return '—';
  const { showSymbol = false, suffix = '' } = options;
  const absVal = Math.abs(val);
  let formatted: string;
  if (absVal >= 1e12) {
    formatted = `${(val / 1e12).toFixed(2)}T`;
  } else if (absVal >= 1e9) {
    formatted = `${(val / 1e9).toFixed(2)}B`;
  } else if (absVal >= 1e6) {
    formatted = `${(val / 1e6).toFixed(2)}M`;
  } else if (absVal >= 1e3) {
    formatted = `${(val / 1e3).toFixed(1)}K`;
  } else {
    formatted = val.toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: val % 1 === 0 ? 0 : 2,
    });
  }
  return `${showSymbol ? '$' : ''}${formatted}${suffix}`;
}

/**
 * Format currency with full numeric precision (no magnitude abbreviation).
 * Use for tooltips or contexts requiring exact values.
 */
export function formatCurrencyRaw(
  val: number | null | undefined,
  options: { showSymbol?: boolean } = {}
): string {
  if (val == null || isNaN(val)) return '—';
  const { showSymbol = false } = options;
  const formatted = val.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: val % 1 === 0 ? 0 : 2,
  });
  return `${showSymbol ? '$' : ''}${formatted}`;
}

/**
 * Format percentage string (+28.0% or -13.6%)
 */
export function formatPercent(val: number | null | undefined, includeSign: boolean = true): string {
  if (val == null || isNaN(val)) return '—';
  const sign = includeSign && val > 0 ? '+' : '';
  return `${sign}${val.toFixed(1)}%`;
}

/**
 * Format standard ratio (e.g. 2.23)
 */
export function formatRatio(val: number | null | undefined): string {
  if (val == null || isNaN(val)) return '—';
  return val.toFixed(2);
}

/**
 * Generates verified deterministic Key Facts directly from structured financial metrics.
 * Zero LLM hallucination: figures and percentages are directly calculated.
 */
export function generateDeterministicKeyFacts(data: ParsedFinancialData): Array<{ title: string; desc: string; trend: 'up' | 'down' | 'neutral' }> {
  const facts: Array<{ title: string; desc: string; trend: 'up' | 'down' | 'neutral' }> = [];
  const { primaryMetrics, ratios, periods, periodMetrics } = data;

  const curPeriod = periods[0];
  const prevPeriod = periods[1];

  const getMetricPair = (key: string) => {
    if (curPeriod && prevPeriod && periodMetrics[curPeriod]?.[key] != null && periodMetrics[prevPeriod]?.[key] != null) {
      return {
        cur: periodMetrics[curPeriod][key],
        prev: periodMetrics[prevPeriod][key],
      };
    }
    return { cur: primaryMetrics[key] ?? null, prev: null };
  };

  // 1. Revenue
  const rev = getMetricPair('revenue');
  if (rev.cur != null) {
    if (rev.prev != null) {
      const delta = calculateDelta(rev.cur, rev.prev);
      if (delta.percentChange != null) {
        const direction = delta.percentChange >= 0 ? 'grew' : 'declined';
        facts.push({
          title: `Revenue ${direction} ${Math.abs(delta.percentChange)}% YoY`,
          desc: `${curPeriod || 'Current period'} revenue reached ${formatCurrency(rev.cur, { showSymbol: true })} compared to ${formatCurrency(rev.prev, { showSymbol: true })} in ${prevPeriod || 'prior period'}.`,
          trend: delta.trend,
        });
      }
    } else {
      facts.push({
        title: `Reported Revenue: ${formatCurrency(rev.cur, { showSymbol: true })}`,
        desc: `Total top-line revenue extracted from financial statements.`,
        trend: 'neutral',
      });
    }
  }

  // 2. Net Income
  const ni = getMetricPair('net_income');
  if (ni.cur != null) {
    if (ni.prev != null) {
      const delta = calculateDelta(ni.cur, ni.prev);
      if (delta.percentChange != null) {
        const direction = delta.percentChange >= 0 ? 'increased' : 'declined';
        facts.push({
          title: `Net income ${direction} ${Math.abs(delta.percentChange)}% YoY`,
          desc: `Net earnings stood at ${formatCurrency(ni.cur, { showSymbol: true })} vs ${formatCurrency(ni.prev, { showSymbol: true })} in the prior reporting period.`,
          trend: delta.trend,
        });
      }
    } else {
      facts.push({
        title: `Reported Net Income: ${formatCurrency(ni.cur, { showSymbol: true })}`,
        desc: `Bottom-line net earnings recorded for the period.`,
        trend: 'neutral',
      });
    }
  }

  // 3. Balance Sheet Expansion (Assets vs Liabilities)
  const assets = getMetricPair('total_assets');
  const liab = getMetricPair('total_liabilities');
  if (assets.cur != null && liab.cur != null) {
    if (assets.prev != null && liab.prev != null) {
      const aDelta = calculateDelta(assets.cur, assets.prev);
      const lDelta = calculateDelta(liab.cur, liab.prev);
      if (aDelta.percentChange != null && lDelta.percentChange != null) {
        const desc = `Total assets changed ${formatPercent(aDelta.percentChange)} to ${formatCurrency(assets.cur, { showSymbol: true })}, while total liabilities changed ${formatPercent(lDelta.percentChange)} to ${formatCurrency(liab.cur, { showSymbol: true })}.`;
        facts.push({
          title: 'Balance Sheet Trajectory',
          desc,
          trend: aDelta.trend,
        });
      }
    } else {
      facts.push({
        title: 'Balance Sheet Structure',
        desc: `Total assets of ${formatCurrency(assets.cur, { showSymbol: true })} against total liabilities of ${formatCurrency(liab.cur, { showSymbol: true })}.`,
        trend: 'neutral',
      });
    }
  }

  // 4. Liquidity & Leverage
  const curRatio = ratios['current_ratio'];
  const dte = ratios['debt_to_equity'];
  if (curRatio != null || dte != null) {
    const parts: string[] = [];
    if (curRatio != null) parts.push(`Current ratio of ${formatRatio(curRatio)}`);
    if (dte != null) parts.push(`Debt-to-Equity ratio of ${formatRatio(dte)}`);
    facts.push({
      title: 'Capital Structure & Liquidity',
      desc: `${parts.join(' and ')}, calculated deterministically from balance sheet items.`,
      trend: curRatio != null && curRatio >= 1.5 ? 'up' : 'neutral',
    });
  }

  // 5. Operating & Profitability Margins
  const gm = ratios['gross_margin_pct'];
  const om = ratios['operating_margin_pct'];
  const nm = ratios['net_margin_pct'];
  if (gm != null || om != null || nm != null) {
    const marginParts: string[] = [];
    if (gm != null) marginParts.push(`Gross margin ${formatPercent(gm, false)}`);
    if (om != null) marginParts.push(`Operating margin ${formatPercent(om, false)}`);
    if (nm != null) marginParts.push(`Net margin ${formatPercent(nm, false)}`);
    facts.push({
      title: 'Operating Efficiency',
      desc: `${marginParts.join(' | ')}.`,
      trend: nm != null && nm > 15 ? 'up' : 'neutral',
    });
  }

  return facts;
}
