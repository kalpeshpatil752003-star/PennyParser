import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Footer } from './Footer';

const PAGE_TITLES: Record<string, string> = {
  '/documents': 'Documents',
  '/research': 'Research',
  '/analysis': 'Analysis',
};

export function AppLayout() {
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] || '';

  return (
    <div className="min-h-screen flex w-full font-sans text-[#111111] bg-[#F5F4F0] dark:text-[#F2F2F0] dark:bg-[#111111] transition-colors duration-200">
      <Sidebar />
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <Topbar pageTitle={pageTitle} />
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
        <Footer />
      </main>
    </div>
  );
}