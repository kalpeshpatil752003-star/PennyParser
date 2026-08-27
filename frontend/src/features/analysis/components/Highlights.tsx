import { ArrowUp, ArrowDown, ArrowRight, Minus } from 'lucide-react';
import type { ParsedFinancialData } from '../utils/financialCalculations';
import { generateDeterministicKeyFacts } from '../utils/financialCalculations';

interface HighlightProps {
  title: string;
  desc: string;
  trend: 'up' | 'down' | 'neutral';
}

function HighlightBox({ title, desc, trend }: HighlightProps) {
  const isUp = trend === 'up';
  const isDown = trend === 'down';

  return (
    <div className="flex gap-4">
      <div
        className={`mt-0.5 flex items-center justify-center w-6 h-6 rounded-full border shrink-0 ${
          isUp
            ? 'border-green-600/30 text-green-600 bg-green-600/10 dark:border-green-500/30 dark:text-green-500 dark:bg-green-500/10'
            : isDown
            ? 'border-penny-accent/30 text-penny-accent bg-penny-accent/10 dark:border-penny-dark-accent/30 dark:text-penny-dark-accent dark:bg-penny-dark-accent/10'
            : 'border-penny-border text-[#666666] dark:text-[#999999] bg-penny-bg dark:bg-penny-dark-bg'
        }`}
      >
        {isUp ? <ArrowUp size={12} /> : isDown ? <ArrowDown size={12} /> : <Minus size={12} />}
      </div>
      <div>
        <h4 className="text-sm font-medium mb-1">{title}</h4>
        <p className="text-xs text-[#666666] dark:text-[#999999] leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

interface HighlightsProps {
  data: ParsedFinancialData;
  onViewKeyFacts?: () => void;
}

export function Highlights({ data, onViewKeyFacts }: HighlightsProps) {
  const facts = generateDeterministicKeyFacts(data);
  const displayFacts = facts.slice(0, 3);

  if (displayFacts.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-penny-border dark:border-penny-dark-border pt-10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-[10px] uppercase tracking-widest font-semibold">Key Highlights</h3>
        <span className="text-[10px] text-[#666666] dark:text-[#999999] uppercase tracking-wider">
          Deterministic Insights
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {displayFacts.map((fact, idx) => (
          <HighlightBox key={idx} title={fact.title} desc={fact.desc} trend={fact.trend} />
        ))}
      </div>

      {onViewKeyFacts && (
        <button
          type="button"
          onClick={onViewKeyFacts}
          className="text-[10px] text-penny-accent dark:text-penny-dark-accent font-medium flex items-center gap-1 mt-6 uppercase tracking-wider hover:opacity-80 transition-opacity cursor-pointer"
        >
          View all key facts <ArrowRight size={12} />
        </button>
      )}
    </div>
  );
}