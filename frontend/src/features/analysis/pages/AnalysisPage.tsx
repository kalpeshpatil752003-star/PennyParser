import { ChevronDown, Download } from 'lucide-react';
import { MetricsRow } from '../components/MetricsRow';
import { TrendChart } from '../components/TrendChart';
import { BalanceSheetTable, RatioTable } from '../components/FinancialTables';
import { Highlights } from '../components/Highlights';

export function AnalysisPage() {
  const tabs = ['Overview', 'Financial Statements', 'Ratios', 'Trends', 'Key Facts', 'Comparisons'];

  return (
    <div className="p-10 max-w-[1400px] mx-auto h-full overflow-y-auto">
      {/* Header Area */}
      <div className="flex justify-between items-end mb-10">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-3">Document</div>
          <h1 className="text-3xl font-medium tracking-tight">Meta Platforms, Inc.</h1>
          <div className="text-lg text-[#666666] dark:text-[#999999] mb-2">Q2 / 2026 Results</div>
          <div className="flex gap-4 text-xs text-[#666666] dark:text-[#999999]">
            <span>Filed Jul 29, 2026</span>
            <span>•</span>
            <span>USD in millions</span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-end gap-6">
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999]">Period</label>
            <button className="flex items-center justify-between w-32 border border-penny-border dark:border-penny-dark-border px-3 py-1.5 text-xs bg-penny-surface dark:bg-penny-dark-surface hover:bg-penny-border/20 transition-colors">
              Q2 2026 <ChevronDown size={14} />
            </button>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999]">Compare With</label>
            <button className="flex items-center justify-between w-32 border border-penny-border dark:border-penny-dark-border px-3 py-1.5 text-xs bg-penny-surface dark:bg-penny-dark-surface hover:bg-penny-border/20 transition-colors">
              Q2 2025 <ChevronDown size={14} />
            </button>
          </div>
          <button className="flex items-center gap-2 border border-penny-text dark:border-penny-dark-text text-penny-text dark:text-penny-dark-text px-4 py-1.5 text-xs font-medium hover:bg-penny-text hover:text-penny-bg dark:hover:bg-penny-dark-text dark:hover:text-penny-dark-bg transition-colors">
            <Download size={14} /> Export
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-8 border-b border-penny-border dark:border-penny-dark-border mb-10">
        {tabs.map((tab, i) => (
          <button 
            key={tab} 
            className={`pb-3 text-xs font-medium transition-colors ${
              i === 0 
                ? 'border-b-2 border-penny-accent dark:border-penny-dark-accent text-penny-text dark:text-penny-dark-text' 
                : 'text-[#666666] dark:text-[#999999] hover:text-penny-text dark:hover:text-penny-dark-text'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <MetricsRow />

      {/* Grid Content */}
      <div className="grid grid-cols-3 gap-10 mb-10">
        <TrendChart />
        <BalanceSheetTable />
        <RatioTable />
      </div>

      <Highlights />
      
      {/* Padding at the bottom for scrolling */}
      <div className="h-10"></div>
    </div>
  );
}