interface MetricProps {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
}

function MetricBox({ label, value, change, trend }: MetricProps) {
  const isUp = trend === 'up';
  return (
    <div className="p-6">
      <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-3">
        {label}
      </div>
      <div className="font-mono text-2xl mb-1">${value}</div>
      <div className={`text-[10px] font-mono ${isUp ? 'text-green-600 dark:text-green-500' : 'text-penny-accent dark:text-penny-dark-accent'}`}>
        {change} YoY
      </div>
    </div>
  );
}

export function MetricsRow() {
  return (
    <div className="grid grid-cols-5 border-y border-penny-border dark:border-penny-dark-border divide-x divide-penny-border dark:divide-penny-dark-border mb-10 bg-penny-surface dark:bg-penny-dark-surface">
      <MetricBox label="Revenue" value="60,801M" change="+28.0%" trend="up" />
      <MetricBox label="Net Income" value="15,848M" change="-13.6%" trend="down" />
      <MetricBox label="Operating Income" value="18,638M" change="-8.0%" trend="down" />
      <MetricBox label="Total Assets" value="449,956M" change="+22.9%" trend="up" />
      <MetricBox label="Total Liabilities" value="188,735M" change="+26.8%" trend="up" />
    </div>
  );
}