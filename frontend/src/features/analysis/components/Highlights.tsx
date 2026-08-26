import { ArrowUp, ArrowDown, ArrowRight } from 'lucide-react';

interface HighlightProps {
  title: string;
  desc: string;
  trend: 'up' | 'down';
}

function HighlightBox({ title, desc, trend }: HighlightProps) {
  const isUp = trend === 'up';
  return (
    <div className="flex gap-4">
      <div className={`mt-0.5 flex items-center justify-center w-6 h-6 rounded-full border ${isUp ? 'border-green-600/30 text-green-600 bg-green-600/10 dark:border-green-500/30 dark:text-green-500 dark:bg-green-500/10' : 'border-penny-accent/30 text-penny-accent bg-penny-accent/10 dark:border-penny-dark-accent/30 dark:text-penny-dark-accent dark:bg-penny-dark-accent/10'}`}>
        {isUp ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
      </div>
      <div>
        <h4 className="text-sm font-medium mb-1">{title}</h4>
        <p className="text-xs text-[#666666] dark:text-[#999999] leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

export function Highlights() {
  return (
    <div className="border-t border-penny-border dark:border-penny-dark-border pt-10">
      <h3 className="text-[10px] uppercase tracking-widest font-semibold mb-6">Key Highlights</h3>
      <div className="grid grid-cols-3 gap-10">
        <HighlightBox 
          title="Revenue grew 28% YoY" 
          desc="Q2 2026 revenue increased to $60,801M compared to $47,516M in Q2 2025."
          trend="up" 
        />
        <HighlightBox 
          title="Net income declined 13.6% YoY" 
          desc="Q2 2026 net income was $15,848M compared to $18,342M in Q2 2025."
          trend="down" 
        />
        <HighlightBox 
          title="Strong balance sheet expansion" 
          desc="Total assets increased 22.9% YoY to reach a total of $449,956M."
          trend="up" 
        />
      </div>
      <button className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity">
        View key facts <ArrowRight size={12} />
      </button>
    </div>
  );
}