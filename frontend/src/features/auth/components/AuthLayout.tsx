import type { ReactNode } from 'react';

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-penny-bg text-penny-text font-sans">
      {/* Left Panel */}
      <div className="w-full md:w-[45%] p-10 md:p-16 flex flex-col justify-between min-h-[30vh] md:min-h-screen border-b md:border-b-0 md:border-r border-penny-border">
        
        {/* Brand */}
        <div>
          <h1 className="text-lg font-medium leading-none tracking-tight">
            PENNY <br />
            PARSER <span className="text-penny-accent">/</span>
          </h1>
        </div>

        {/* Editorial Text */}
        <div className="mt-16 md:mt-0">
          <div className="flex items-center gap-4 text-[10px] uppercase tracking-widest font-semibold mb-6">
            <span className="text-penny-accent">01</span>
            <span className="text-penny-border">/</span>
            <span>Access</span>
          </div>
          
          <hr className="border-t border-penny-border mb-6 w-full max-w-sm" />
          
          <h2 className="text-2xl font-medium tracking-tight mb-4 uppercase">
            Financial Document<br />Intelligence
          </h2>
          <p className="text-sm text-[#666666] leading-relaxed max-w-xs">
            Upload. Analyze. Ask. Understand your financial documents with precision.
          </p>
        </div>

        {/* Footer */}
        <div className="hidden md:block">
          <div className="text-[10px] uppercase tracking-widest font-semibold mb-4">
            © 2026 Penny Parser
          </div>
          <hr className="border-t border-penny-border w-64" />
        </div>
      </div>

      {/* Right Panel (Form Container) */}
      <div className="w-full md:w-[55%] p-10 md:p-16 flex flex-col justify-center">
        <div className="w-full max-w-sm mx-auto">
          {children}
        </div>
      </div>
    </div>
  );
}