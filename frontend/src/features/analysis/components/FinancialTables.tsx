import { ArrowRight, CheckCircle2 } from 'lucide-react';
import type { ParsedFinancialData } from '../utils/financialCalculations';
import {
  calculateDelta,
  formatCurrency,
  formatPercent,
  formatRatio,
  METRIC_LABELS,
} from '../utils/financialCalculations';

interface TableRowProps {
  label: string;
  val: number | null | undefined;
  prevVal: number | null | undefined;
  isPercent?: boolean;
}

function TableRow({ label, val, prevVal, isPercent }: TableRowProps) {
  const delta = calculateDelta(val, prevVal);
  const isUp = delta.trend === 'up';
  const isDown = delta.trend === 'down';

  return (
    <tr>
      <td className="py-3 font-sans text-xs">{label}</td>
      <td className="py-3 text-right font-mono">
        {val != null ? (isPercent ? formatPercent(val, false) : formatCurrency(val)) : '—'}
      </td>
      <td className="py-3 text-right font-mono text-[#666666] dark:text-[#999999]">
        {prevVal != null ? (isPercent ? formatPercent(prevVal, false) : formatCurrency(prevVal)) : '—'}
      </td>
      <td
        className={`py-3 text-right font-mono ${
          isUp
            ? 'text-green-600 dark:text-green-500'
            : isDown
            ? 'text-penny-accent dark:text-penny-dark-accent'
            : 'text-[#666666] dark:text-[#999999]'
        }`}
      >
        {delta.percentChange != null ? formatPercent(delta.percentChange) : '—'}
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Overview Cards
// ---------------------------------------------------------------------------

interface BalanceSheetTableProps {
  data: ParsedFinancialData;
  selectedPeriod?: string;
  comparePeriod?: string;
  onViewBalanceSheet?: () => void;
}

export function BalanceSheetTable({
  data,
  selectedPeriod,
  comparePeriod,
  onViewBalanceSheet,
}: BalanceSheetTableProps) {
  const { periods, periodMetrics, primaryMetrics } = data;
  const curPeriod = selectedPeriod || periods[0] || 'Current';
  const prevPeriod = comparePeriod || periods[1] || 'Previous';

  const getVal = (key: string, p?: string) => {
    if (p && periodMetrics[p]?.[key] != null) return periodMetrics[p][key];
    if (!p || p === curPeriod) return primaryMetrics[key] ?? null;
    return null;
  };

  return (
    <div className="col-span-1 border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-6 flex flex-col justify-between">
      <div>
        <h3 className="text-[10px] uppercase tracking-widest font-semibold mb-1">Balance Sheet Summary</h3>
        <div className="text-[10px] text-[#666666] dark:text-[#999999] mb-6">USD in millions</div>
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-penny-border dark:border-penny-dark-border">
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 w-2/5"></th>
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 text-right">{curPeriod}</th>
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 text-right">{prevPeriod}</th>
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 text-right">Change</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-penny-border dark:divide-penny-dark-border font-mono text-[11px]">
            <TableRow
              label="Total Assets"
              val={getVal('total_assets', curPeriod)}
              prevVal={getVal('total_assets', prevPeriod)}
            />
            <TableRow
              label="Total Liabilities"
              val={getVal('total_liabilities', curPeriod)}
              prevVal={getVal('total_liabilities', prevPeriod)}
            />
            <TableRow
              label="Stockholders' Equity"
              val={getVal('total_equity', curPeriod)}
              prevVal={getVal('total_equity', prevPeriod)}
            />
            <TableRow
              label="Current Assets"
              val={getVal('current_assets', curPeriod)}
              prevVal={getVal('current_assets', prevPeriod)}
            />
            <TableRow
              label="Current Liabilities"
              val={getVal('current_liabilities', curPeriod)}
              prevVal={getVal('current_liabilities', prevPeriod)}
            />
          </tbody>
        </table>
      </div>
      {onViewBalanceSheet && (
        <button
          type="button"
          onClick={onViewBalanceSheet}
          className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity cursor-pointer"
        >
          View balance sheet <ArrowRight size={12} />
        </button>
      )}
    </div>
  );
}

function RatioRow({ label, val }: { label: string; val: string }) {
  return (
    <div className="py-3 flex justify-between items-center text-xs">
      <span className="font-sans">{label}</span>
      <span className="font-mono">{val}</span>
    </div>
  );
}

interface RatioTableProps {
  data: ParsedFinancialData;
  onViewAllRatios?: () => void;
}

export function RatioTable({ data, onViewAllRatios }: RatioTableProps) {
  const { ratios } = data;

  return (
    <div className="col-span-1 border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-6 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-[10px] uppercase tracking-widest font-semibold">Key Ratios</h3>
          <span className="text-[9px] uppercase tracking-wider text-green-600 dark:text-green-500 font-mono">
            Deterministic
          </span>
        </div>
        <div className="flex flex-col divide-y divide-penny-border dark:divide-penny-dark-border">
          <RatioRow label="Current Ratio" val={formatRatio(ratios['current_ratio'])} />
          <RatioRow label="Debt to Equity" val={formatRatio(ratios['debt_to_equity'])} />
          <RatioRow label="Gross Margin" val={formatPercent(ratios['gross_margin_pct'], false)} />
          <RatioRow label="Operating Margin" val={formatPercent(ratios['operating_margin_pct'], false)} />
          <RatioRow label="Net Margin" val={formatPercent(ratios['net_margin_pct'], false)} />
          <RatioRow label="Return on Assets (ROA)" val={formatPercent(ratios['roa_pct'], false)} />
          <RatioRow label="Return on Equity (ROE)" val={formatPercent(ratios['roe_pct'], false)} />
        </div>
      </div>
      {onViewAllRatios && (
        <button
          type="button"
          onClick={onViewAllRatios}
          className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity cursor-pointer"
        >
          View all ratios <ArrowRight size={12} />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Full Tabs Views
// ---------------------------------------------------------------------------

interface StatementsTabProps {
  data: ParsedFinancialData;
  selectedPeriod?: string;
  comparePeriod?: string;
}

export function FinancialStatementsTab({ data, selectedPeriod, comparePeriod }: StatementsTabProps) {
  const { periods, periodMetrics, primaryMetrics } = data;
  const curPeriod = selectedPeriod || periods[0] || 'Current Period';
  const prevPeriod = comparePeriod || periods[1] || 'Prior Period';

  const getVal = (key: string, p?: string) => {
    if (p && periodMetrics[p]?.[key] != null) return periodMetrics[p][key];
    if (!p || p === curPeriod) return primaryMetrics[key] ?? null;
    return null;
  };

  return (
    <div className="flex flex-col gap-12">
      {/* Income Statement */}
      <div className="border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-8">
        <div className="flex justify-between items-end mb-6 pb-4 border-b border-penny-border dark:border-penny-dark-border">
          <div>
            <h3 className="text-base font-medium tracking-tight">Income Statement</h3>
            <div className="text-xs text-[#666666] dark:text-[#999999] mt-1">
              Extracted statement of operations (USD in millions, except EPS)
            </div>
          </div>
        </div>

        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-penny-border dark:border-penny-dark-border text-[#666666] dark:text-[#999999]">
              <th className="font-normal pb-3 w-2/5">Line Item</th>
              <th className="font-normal pb-3 text-right">{curPeriod}</th>
              <th className="font-normal pb-3 text-right">{prevPeriod}</th>
              <th className="font-normal pb-3 text-right">Change ($)</th>
              <th className="font-normal pb-3 text-right">Change (%)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-penny-border dark:divide-penny-dark-border font-mono text-xs">
            {['revenue', 'cost_of_goods_sold', 'gross_profit', 'operating_income', 'net_income', 'eps'].map((key) => {
              const val = getVal(key, curPeriod);
              const prev = getVal(key, prevPeriod);
              const delta = calculateDelta(val, prev);
              const isUp = delta.trend === 'up';
              const isDown = delta.trend === 'down';
              const isEps = key === 'eps';

              return (
                <tr key={key} className="hover:bg-penny-border/10">
                  <td className="py-3.5 font-sans font-medium text-penny-text dark:text-penny-dark-text">
                    {METRIC_LABELS[key]?.label || key}
                  </td>
                  <td className="py-3.5 text-right font-mono">
                    {val != null ? (isEps ? `$${val.toFixed(2)}` : formatCurrency(val)) : '—'}
                  </td>
                  <td className="py-3.5 text-right font-mono text-[#666666] dark:text-[#999999]">
                    {prev != null ? (isEps ? `$${prev.toFixed(2)}` : formatCurrency(prev)) : '—'}
                  </td>
                  <td className="py-3.5 text-right font-mono">
                    {delta.absoluteChange != null ? (isEps ? `$${delta.absoluteChange.toFixed(2)}` : formatCurrency(delta.absoluteChange)) : '—'}
                  </td>
                  <td
                    className={`py-3.5 text-right font-mono ${
                      isUp
                        ? 'text-green-600 dark:text-green-500'
                        : isDown
                        ? 'text-penny-accent dark:text-penny-dark-accent'
                        : 'text-[#666666] dark:text-[#999999]'
                    }`}
                  >
                    {delta.percentChange != null ? formatPercent(delta.percentChange) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Balance Sheet */}
      <div className="border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-8">
        <div className="flex justify-between items-end mb-6 pb-4 border-b border-penny-border dark:border-penny-dark-border">
          <div>
            <h3 className="text-base font-medium tracking-tight">Balance Sheet</h3>
            <div className="text-xs text-[#666666] dark:text-[#999999] mt-1">
              Consolidated balance sheet positions (USD in millions)
            </div>
          </div>
        </div>

        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-penny-border dark:border-penny-dark-border text-[#666666] dark:text-[#999999]">
              <th className="font-normal pb-3 w-2/5">Line Item</th>
              <th className="font-normal pb-3 text-right">{curPeriod}</th>
              <th className="font-normal pb-3 text-right">{prevPeriod}</th>
              <th className="font-normal pb-3 text-right">Change ($)</th>
              <th className="font-normal pb-3 text-right">Change (%)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-penny-border dark:divide-penny-dark-border font-mono text-xs">
            {['current_assets', 'total_assets', 'current_liabilities', 'total_liabilities', 'total_equity'].map((key) => {
              const val = getVal(key, curPeriod);
              const prev = getVal(key, prevPeriod);
              const delta = calculateDelta(val, prev);
              const isUp = delta.trend === 'up';
              const isDown = delta.trend === 'down';

              return (
                <tr key={key} className="hover:bg-penny-border/10">
                  <td className="py-3.5 font-sans font-medium text-penny-text dark:text-penny-dark-text">
                    {METRIC_LABELS[key]?.label || key}
                  </td>
                  <td className="py-3.5 text-right font-mono">{formatCurrency(val)}</td>
                  <td className="py-3.5 text-right font-mono text-[#666666] dark:text-[#999999]">
                    {formatCurrency(prev)}
                  </td>
                  <td className="py-3.5 text-right font-mono">{formatCurrency(delta.absoluteChange)}</td>
                  <td
                    className={`py-3.5 text-right font-mono ${
                      isUp
                        ? 'text-green-600 dark:text-green-500'
                        : isDown
                        ? 'text-penny-accent dark:text-penny-dark-accent'
                        : 'text-[#666666] dark:text-[#999999]'
                    }`}
                  >
                    {delta.percentChange != null ? formatPercent(delta.percentChange) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function RatiosTab({ data }: { data: ParsedFinancialData }) {
  const { ratios } = data;

  const categories = [
    {
      title: 'LIQUIDITY',
      subtitle: 'Ability to cover short-term financial obligations',
      items: [
        {
          name: 'Current Ratio',
          formula: 'Current Assets / Current Liabilities',
          value: formatRatio(ratios['current_ratio']),
          benchmark: '≥ 1.5x is generally healthy',
        },
      ],
    },
    {
      title: 'LEVERAGE & SOLVENCY',
      subtitle: 'Capital structure and long-term debt sustainability',
      items: [
        {
          name: 'Debt to Equity',
          formula: 'Total Liabilities / Stockholders Equity',
          value: formatRatio(ratios['debt_to_equity']),
          benchmark: '< 1.0x indicates conservative leverage',
        },
      ],
    },
    {
      title: 'PROFITABILITY & RETURNS',
      subtitle: 'Operating efficiency and capital productivity',
      items: [
        {
          name: 'Gross Margin',
          formula: 'Gross Profit / Revenue × 100',
          value: formatPercent(ratios['gross_margin_pct'], false),
          benchmark: 'Pricing power indicator',
        },
        {
          name: 'Operating Margin',
          formula: 'Operating Income / Revenue × 100',
          value: formatPercent(ratios['operating_margin_pct'], false),
          benchmark: 'Core operational efficiency',
        },
        {
          name: 'Net Margin',
          formula: 'Net Income / Revenue × 100',
          value: formatPercent(ratios['net_margin_pct'], false),
          benchmark: 'Bottom-line profitability',
        },
        {
          name: 'Return on Assets (ROA)',
          formula: 'Net Income / Total Assets × 100',
          value: formatPercent(ratios['roa_pct'], false),
          benchmark: 'Asset deployment productivity',
        },
        {
          name: 'Return on Equity (ROE)',
          formula: 'Net Income / Total Equity × 100',
          value: formatPercent(ratios['roe_pct'], false),
          benchmark: 'Shareholder capital return',
        },
      ],
    },
  ];

  return (
    <div className="flex flex-col gap-10">
      <div className="border-b border-penny-border dark:border-penny-dark-border pb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight">Deterministic Financial Ratios</h2>
          <p className="text-xs text-[#666666] dark:text-[#999999] mt-1">
            Calculated directly from extracted balance sheet and income statement line items without LLM hallucination.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-500 font-mono">
          <CheckCircle2 size={15} />
          <span>Deterministic Reasoning Verified</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {categories.map((cat) => (
          <div
            key={cat.title}
            className="border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-6 flex flex-col justify-between"
          >
            <div>
              <h3 className="text-[10px] uppercase tracking-widest font-semibold mb-1 text-penny-text dark:text-penny-dark-text">
                {cat.title}
              </h3>
              <div className="text-[10px] text-[#666666] dark:text-[#999999] mb-6">{cat.subtitle}</div>

              <div className="flex flex-col divide-y divide-penny-border dark:divide-penny-dark-border">
                {cat.items.map((item) => (
                  <div key={item.name} className="py-4">
                    <div className="flex justify-between items-baseline mb-1">
                      <span className="text-xs font-medium">{item.name}</span>
                      <span className="font-mono text-base font-semibold text-penny-accent dark:text-penny-dark-accent">
                        {item.value}
                      </span>
                    </div>
                    <div className="text-[10px] font-mono text-[#666666] dark:text-[#999999]">
                      Formula: {item.formula}
                    </div>
                    <div className="text-[10px] text-[#888888] dark:text-[#777777] mt-0.5">
                      {item.benchmark}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ComparisonsTab({
  data,
  selectedPeriod,
  comparePeriod,
}: {
  data: ParsedFinancialData;
  selectedPeriod?: string;
  comparePeriod?: string;
}) {
  const { periods, periodMetrics, primaryMetrics } = data;
  const curPeriod = selectedPeriod || periods[0] || 'Current Period';
  const prevPeriod = comparePeriod || periods[1] || 'Prior Period';

  const getVal = (key: string, p?: string) => {
    if (p && periodMetrics[p]?.[key] != null) return periodMetrics[p][key];
    if (!p || p === curPeriod) return primaryMetrics[key] ?? null;
    return null;
  };

  const metricKeys = Object.keys(METRIC_LABELS).filter((k) => !METRIC_LABELS[k].label.includes('Margin'));

  return (
    <div className="border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-8">
      <div className="flex justify-between items-end mb-8 pb-4 border-b border-penny-border dark:border-penny-dark-border">
        <div>
          <h2 className="text-xl font-medium tracking-tight">Period Comparison</h2>
          <p className="text-xs text-[#666666] dark:text-[#999999] mt-1">
            Deterministic delta and percentage calculations between {curPeriod} and {prevPeriod}.
          </p>
        </div>
      </div>

      <table className="w-full text-xs text-left border-collapse">
        <thead>
          <tr className="border-b border-penny-border dark:border-penny-dark-border text-[#666666] dark:text-[#999999]">
            <th className="font-normal pb-3 w-1/3">Financial Metric</th>
            <th className="font-normal pb-3 text-right">{curPeriod}</th>
            <th className="font-normal pb-3 text-right">{prevPeriod}</th>
            <th className="font-normal pb-3 text-right">Absolute Change ($)</th>
            <th className="font-normal pb-3 text-right">Percentage Change (%)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-penny-border dark:divide-penny-dark-border font-mono text-xs">
          {metricKeys.map((key) => {
            const val = getVal(key, curPeriod);
            const prev = getVal(key, prevPeriod);
            const delta = calculateDelta(val, prev);
            const isUp = delta.trend === 'up';
            const isDown = delta.trend === 'down';

            return (
              <tr key={key} className="hover:bg-penny-border/10">
                <td className="py-3.5 font-sans font-medium text-penny-text dark:text-penny-dark-text">
                  {METRIC_LABELS[key]?.label || key}
                </td>
                <td className="py-3.5 text-right font-mono">{formatCurrency(val)}</td>
                <td className="py-3.5 text-right font-mono text-[#666666] dark:text-[#999999]">
                  {formatCurrency(prev)}
                </td>
                <td className="py-3.5 text-right font-mono">{formatCurrency(delta.absoluteChange)}</td>
                <td
                  className={`py-3.5 text-right font-mono font-semibold ${
                    isUp
                      ? 'text-green-600 dark:text-green-500'
                      : isDown
                      ? 'text-penny-accent dark:text-penny-dark-accent'
                      : 'text-[#666666] dark:text-[#999999]'
                  }`}
                >
                  {delta.percentChange != null ? formatPercent(delta.percentChange) : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}