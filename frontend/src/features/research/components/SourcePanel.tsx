import { ArrowUpRight, FileText } from 'lucide-react';
import type { Citation, Document } from '../../../types';

interface SourcePanelProps {
  citations?: Citation[];
  document?: Document | null;
}

export function SourcePanel({ citations = [], document }: SourcePanelProps) {
  // Deduplicate citations by (documentId, page)
  const uniqueCitations = citations.filter(
    (c, idx, arr) =>
      arr.findIndex((other) => other.documentId === c.documentId && other.page === c.page) === idx
  );

  return (
    <aside className="w-80 flex flex-col bg-penny-surface dark:bg-penny-dark-surface border-l border-penny-border dark:border-penny-dark-border">
      <div className="p-6 border-b border-penny-border dark:border-penny-dark-border">
        <h2 className="text-[10px] uppercase tracking-widest font-semibold">Sources & Citations</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        {uniqueCitations.length > 0 ? (
          uniqueCitations.map((cit, idx) => {
            const pageStr = String(cit.page || idx + 1).padStart(2, '0');
            return (
              <div key={`${cit.documentId}-${cit.page}-${idx}`} className="flex flex-col gap-2">
                <div className="flex items-center justify-between border-b border-penny-border dark:border-penny-dark-border pb-2">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs border border-penny-border dark:border-penny-dark-border px-2 py-1 bg-penny-bg dark:bg-penny-dark-bg">
                      {pageStr}
                    </span>
                    <span className="text-xs font-medium">Page {cit.page}</span>
                  </div>
                  <ArrowUpRight size={14} className="text-[#666666] dark:text-[#999999]" />
                </div>
                <div className="text-xs leading-relaxed text-[#666666] dark:text-[#999999]">
                  <span className="text-penny-text dark:text-penny-dark-text font-medium block mb-1">
                    {document?.fileName || `Document #${cit.documentId}`}
                  </span>
                  Verified excerpt referenced in answer
                </div>
              </div>
            );
          })
        ) : (
          <div className="flex flex-col items-center justify-center text-center py-12 px-2 text-[#666666] dark:text-[#999999]">
            <FileText size={28} strokeWidth={1.2} className="mb-3 opacity-40" />
            <div className="text-xs font-medium mb-1">No Sources Cited Yet</div>
            <div className="text-[11px] leading-relaxed opacity-70">
              When you ask questions, verified page citations will appear here.
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}