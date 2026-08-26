import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { ArrowRight } from 'lucide-react';

const chartData = [
  { name: 'Q2 2025', revenue: 47516 },
  { name: 'Q2 2026', revenue: 60801 },
];

export function TrendChart() {
  return (
    <div className="col-span-1 border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-6 flex flex-col">
      <h3 className="text-[10px] uppercase tracking-widest font-semibold mb-1">Revenue Trend</h3>
      <div className="text-[10px] text-[#666666] dark:text-[#999999] mb-6">USD in millions</div>
      <div className="flex-1 min-h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#666' }} dy={10} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#666' }} />
            <Line type="monotone" dataKey="revenue" stroke="#E53935" strokeWidth={2} dot={{ r: 4, fill: '#E53935' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <button className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity">
        View full trend <ArrowRight size={12} />
      </button>
    </div>
  );
}