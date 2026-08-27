import type { ParsedFinancialData } from '../utils/financialCalculations';
import { calculateDelta, formatCurrency, formatPercent } from '../utils/financialCalculations';

interface MetricsRowProps {
  data: ParsedFinancialData;
  selectedPeriod?: string;
  comparePeriod?: string;
}

interface MetricBoxProps {
  label: string;
  value: number | null | undefined;
  prevValue: number | null | undefined;
}

function MetricBox({ label, value, prevValue }: MetricBoxProps) {
  const delta = calculateDelta(value, prevValue);
  const isUp = delta.trend === 'up';
  const isDown = delta.trend === 'down';

  return (
    <div className="p-6">
      <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-3 truncate">
        {label}
      </div>
      <div className="font-mono text-2xl mb-1 truncate">
        {value != null ? `$${formatCurrency(value)}M` : '—'}
      </div>
      <div
        className={`text-[10px] font-mono ${
          isUp
            ? 'text-green-600 dark:text-green-500'
            : isDown
            ? 'text-penny-accent dark:text-penny-dark-accent'
            : 'text-[#666666] dark:text-[#999999]'
        }`}
      >
        {delta.percentChange != null ? `${formatPercent(delta.percentChange)} YoY` : '— YoY'}
      </div>
    </div>
  );
}

export function MetricsRow({ data, selectedPeriod, comparePeriod }: MetricsRowProps) {
  const { primaryMetrics, periodMetrics, periods } = data;

  const curPeriod = selectedPeriod || periods[0];
  const prevPeriod = comparePeriod || periods[1];

  const getValue = (key: string, period?: string) => {
    if (period && periodMetrics[period]?.[key] != null) {
      return periodMetrics[period][key];
    }
    if (!period || period === curPeriod) {
      return primaryMetrics[key] ?? null;
    }
    return null;
  };

  const revenue = getValue('revenue', curPeriod);
  const prevRevenue = getValue('revenue', prevPeriod);

  const netIncome = getValue('net_income', curPeriod);
  const prevNetIncome = getValue('net_income', prevPeriod);

  const opIncome = getValue('operating_income', curPeriod);
  const prevOpIncome = getValue('operating_income', prevPeriod);

  const totalAssets = getValue('total_assets', curPeriod);
  const prevTotalAssets = getValue('total_assets', prevPeriod);

  const totalLiabilities = getValue('total_liabilities', curPeriod);
  const prevTotalLiabilities = getValue('total_liabilities', prevPeriod);

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 border-y border-penny-border dark:border-penny-dark-border divide-y md:divide-y-0 md:divide-x divide-penny-border dark:divide-penny-dark-border mb-10 bg-penny-surface dark:bg-penny-dark-surface">
      <MetricBox label="Revenue" value={revenue} prevValue={prevRevenue} />
      <MetricBox label="Net Income" value={netIncome} prevValue={prevNetIncome} />
      <MetricBox label="Operating Income" value={opIncome} prevValue={prevOpIncome} />
      <MetricBox label="Total Assets" value={totalAssets} prevValue={prevTotalAssets} />
      <MetricBox label="Total Liabilities" value={totalLiabilities} prevValue={prevTotalLiabilities} />
    </div>
  );
}