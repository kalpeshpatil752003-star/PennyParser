import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import type { Citation } from '../../../types';

interface MessageProps {
  role: 'USER' | 'ASSISTANT';
  time?: string;
  content: React.ReactNode;
  calculation?: React.ReactNode;
  sourcePage?: string;
  sourceNumber?: string;
  citations?: Citation[];
  onCitationClick?: (citation: Citation) => void;
}

export function Message({
  role,
  time,
  content,
  calculation,
  sourcePage,
  sourceNumber,
  citations,
  onCitationClick,
}: MessageProps) {
  const isUser = role === 'USER';

  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-between items-baseline">
        <span
          className={`text-[10px] uppercase tracking-widest font-semibold ${
            isUser
              ? 'text-penny-text dark:text-penny-dark-text'
              : 'text-penny-accent dark:text-penny-dark-accent'
          }`}
        >
          {isUser ? 'You' : 'Penny'}
        </span>
        {time && <span className="text-[10px] text-[#666666] dark:text-[#999999]">{time}</span>}
      </div>

      <div className="text-sm leading-relaxed whitespace-pre-wrap">{content}</div>

      {/* Deterministic Math Block (if present) */}
      {calculation && (
        <div className="mt-2 bg-penny-surface dark:bg-penny-dark-surface border border-penny-border dark:border-penny-dark-border p-4">
          <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-2">
            Calculation:
          </div>
          <div className="font-mono text-xs">{calculation}</div>
        </div>
      )}

      {/* Dynamic Citations List (if present) */}
      {citations && citations.length > 0 && (
        <div className="mt-2">
          <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-2">
            {citations.length > 1 ? 'Sources' : 'Source'}
          </div>
          <div className="flex flex-wrap gap-2">
            {citations.map((c, idx) => {
              const numStr = String(c.page || idx + 1).padStart(2, '0');
              return (
                <button
                  key={`${c.documentId}-${c.page}-${idx}`}
                  type="button"
                  onClick={() => onCitationClick?.(c)}
                  className="border border-penny-border dark:border-penny-dark-border px-3 py-1.5 text-xs flex items-center gap-3 bg-penny-surface dark:bg-penny-dark-surface hover:bg-penny-border/30 dark:hover:bg-penny-dark-border/40 transition-colors inline-flex cursor-pointer"
                >
                  <span className="font-mono border-r border-penny-border dark:border-penny-dark-border pr-3">
                    {numStr}
                  </span>
                  <span>Page {c.page}</span>
                  <ArrowUpRight size={12} className="text-[#666666] dark:text-[#999999]" />
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Legacy Inline Source Link (if present and no citations array) */}
      {sourcePage && sourceNumber && (!citations || citations.length === 0) && (
        <div className="mt-2">
          <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-2">Source</div>
          <button
            type="button"
            className="border border-penny-border dark:border-penny-dark-border px-3 py-1.5 text-xs flex items-center gap-3 bg-penny-surface dark:hover:bg-penny-border/30 dark:hover:bg-penny-dark-border/40 transition-colors inline-flex cursor-pointer"
          >
            <span className="font-mono border-r border-penny-border dark:border-penny-dark-border pr-3">
              {sourceNumber}
            </span>
            <span>{sourcePage}</span>
            <ArrowUpRight size={12} className="text-[#666666] dark:text-[#999999]" />
          </button>
        </div>
      )}
    </div>
  );
}