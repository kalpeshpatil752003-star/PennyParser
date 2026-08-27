import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { ArrowRight } from 'lucide-react';
import type { ParsedFinancialData } from '../utils/financialCalculations';
import { formatCurrency } from '../utils/financialCalculations';

interface TrendChartProps {
  data: ParsedFinancialData;
  onViewFullTrend?: () => void;
}

export function TrendChart({ data, onViewFullTrend }: TrendChartProps) {
  const { periods, periodMetrics, primaryMetrics } = data;

  // Build chronological chart data from available periods
  const chartData = [...periods]
    .reverse()
    .map((p) => ({
      name: p,
      revenue: periodMetrics[p]?.['revenue'] ?? null,
      netIncome: periodMetrics[p]?.['net_income'] ?? null,
    }))
    .filter((d) => d.revenue != null || d.netIncome != null);

  // If no period breakdown exists but a primary revenue metric exists
  if (chartData.length === 0 && primaryMetrics['revenue'] != null) {
    chartData.push({
      name: 'Current',
      revenue: primaryMetrics['revenue'],
      netIncome: primaryMetrics['net_income'] ?? null,
    });
  }

  const hasChartData = chartData.length > 0;

  return (
    <div className="col-span-1 border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-6 flex flex-col justify-between">
      <div>
        <h3 className="text-[10px] uppercase tracking-widest font-semibold mb-1">Revenue Trajectory</h3>
        <div className="text-[10px] text-[#666666] dark:text-[#999999] mb-6">USD in millions</div>

        <div className="min-h-[190px] w-full flex items-center justify-center">
          {hasChartData ? (
            <ResponsiveContainer width="100%" height={190}>
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#888' }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#888' }}
                  tickFormatter={(v) => `$${formatCurrency(v)}`}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-penny-surface dark:bg-penny-dark-surface border border-penny-border dark:border-penny-dark-border p-2 text-xs shadow-md">
                          <div className="font-medium text-[10px] uppercase text-[#666666] dark:text-[#999999] mb-1">
                            {payload[0].payload.name}
                          </div>
                          <div className="font-mono text-penny-accent dark:text-penny-dark-accent">
                            Revenue: ${formatCurrency(payload[0].value as number)}M
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke="#E53935"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#E53935' }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center text-xs text-[#666666] dark:text-[#999999] py-12">
              No revenue series data available
            </div>
          )}
        </div>
      </div>

      {onViewFullTrend && (
        <button
          type="button"
          onClick={onViewFullTrend}
          className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity cursor-pointer"
        >
          View full trend <ArrowRight size={12} />
        </button>
      )}
    </div>
  );
}