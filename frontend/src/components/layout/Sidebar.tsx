import { Link, useLocation } from 'react-router-dom';
import { FileText, ChevronDown } from 'lucide-react';

export function Sidebar() {
  const location = useLocation();
  const navItems = [
    { to: '/documents', label: 'Documents', num: '01' },
    { to: '/research', label: 'Research', num: '02' },
    { to: '/analysis', label: 'Analysis', num: '03' },
  ];

  const isNavActive = (to: string) => {
    return location.pathname === to || location.pathname.startsWith(to + '/');
  };

  return (
    <aside className="w-64 flex flex-col border-r border-[#DCDCD7] dark:border-[#303030] bg-[#F5F4F0] dark:bg-[#111111]">
      <div className="p-8 border-b border-[#DCDCD7] dark:border-[#303030]">
        <h1 className="text-lg font-medium leading-none tracking-tight">
          PENNY <br />
          PARSER <span className="text-[#E53935] dark:text-[#FF4B45]">/</span>
        </h1>
      </div>

      <nav className="flex-1 py-8 px-8 flex flex-col gap-6 border-b border-[#DCDCD7] dark:border-[#303030]">
        {navItems.map((item) => {
          const active = isNavActive(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-baseline gap-4 text-sm text-left group transition-colors ${
                active
                  ? 'text-[#E53935] dark:text-[#FF4B45]'
                  : 'text-[#111111] dark:text-[#F2F2F0] hover:text-[#666666] dark:hover:text-[#999999]'
              }`}
            >
              <span className="font-mono text-xs opacity-50">{item.num}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="py-6 px-8">
        <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-4">
          Current Document
        </div>
        <div className="flex items-start justify-between text-left">
          <div className="flex gap-3">
            <FileText size={16} className="mt-0.5 text-[#666666] dark:text-[#999999]" />
            <div>
              <div className="text-sm font-medium">Meta Platforms, Inc.</div>
              <div className="text-xs text-[#666666] dark:text-[#999999] mt-0.5">Q2 / 2026 Results</div>
            </div>
          </div>
          <ChevronDown size={14} className="text-[#666666] dark:text-[#999999]" />
        </div>
      </div>
    </aside>
  );
}