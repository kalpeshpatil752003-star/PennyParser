import { ArrowRight } from 'lucide-react';

function TableRow({ label, val, prevVal, change }: { label: string; val: string; prevVal: string; change: string }) {
  const isUp = change.startsWith('+');
  return (
    <tr>
      <td className="py-3 font-sans text-xs">{label}</td>
      <td className="py-3 text-right">{val}</td>
      <td className="py-3 text-right">{prevVal}</td>
      <td className={`py-3 text-right ${isUp ? 'text-green-600 dark:text-green-500' : 'text-penny-accent dark:text-penny-dark-accent'}`}>
        {change}
      </td>
    </tr>
  );
}

export function BalanceSheetTable() {
  return (
    <div className="col-span-1 border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-6 flex flex-col justify-between">
      <div>
        <h3 className="text-[10px] uppercase tracking-widest font-semibold mb-1">Balance Sheet Summary</h3>
        <div className="text-[10px] text-[#666666] dark:text-[#999999] mb-6">USD in millions</div>
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-penny-border dark:border-penny-dark-border">
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 w-2/5"></th>
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 text-right">Q2 2026</th>
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 text-right">Q2 2025</th>
              <th className="font-normal text-[#666666] dark:text-[#999999] pb-3 text-right">Change</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-penny-border dark:divide-penny-dark-border font-mono text-[11px]">
            <TableRow label="Total Assets" val="449,956" prevVal="366,021" change="+22.9%" />
            <TableRow label="Total Liabilities" val="188,735" prevVal="148,778" change="+26.8%" />
            <TableRow label="Stockholders' Equity" val="261,221" prevVal="217,243" change="+20.2%" />
            <TableRow label="Current Assets" val="125,475" prevVal="108,722" change="+15.4%" />
            <TableRow label="Current Liabilities" val="56,379" prevVal="41,836" change="+34.8%" />
          </tbody>
        </table>
      </div>
      <button className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity">
        View balance sheet <ArrowRight size={12} />
      </button>
    </div>
  );
}

function RatioRow({ label, val }: { label: string, val: string }) {
  return (
    <div className="py-3 flex justify-between items-center text-xs">
      <span className="font-sans">{label}</span>
      <span className="font-mono">{val}</span>
    </div>
  );
}

export function RatioTable() {
  return (
    <div className="col-span-1 border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-6 flex flex-col justify-between">
      <div>
        <h3 className="text-[10px] uppercase tracking-widest font-semibold mb-6">Key Ratios</h3>
        <div className="flex flex-col divide-y divide-penny-border dark:divide-penny-dark-border">
          <RatioRow label="Current Ratio" val="2.23" />
          <RatioRow label="Debt to Equity" val="0.72" />
          <RatioRow label="Gross Margin" val="80.5%" />
          <RatioRow label="Operating Margin" val="30.6%" />
          <RatioRow label="Net Margin" val="26.1%" />
          <RatioRow label="Return on Assets (ROA)" val="7.1%" />
          <RatioRow label="Return on Equity (ROE)" val="16.7%" />
        </div>
      </div>
      <button className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity">
        View all ratios <ArrowRight size={12} />
      </button>
    </div>
  );
}