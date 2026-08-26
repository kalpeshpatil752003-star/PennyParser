import { useState, useEffect, useRef } from 'react';
import { Search, Sun, Moon, Settings, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

interface TopbarProps {
  pageTitle?: string;
}

export function Topbar({ pageTitle }: TopbarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isDarkMode, setIsDarkMode] = useState(() => localStorage.getItem('penny_theme') === 'dark');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('penny_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('penny_theme', 'light');
    }
  }, [isDarkMode]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = () => {
    setIsDropdownOpen(false);
    logout();
    navigate('/login', { replace: true });
  };

  const initials = user?.fullName ? user.fullName.substring(0, 2).toUpperCase() : 'KP';

  return (
    <header className="h-20 border-b border-[#DCDCD7] dark:border-[#303030] flex items-center justify-between px-8 bg-[#F5F4F0] dark:bg-[#111111]">
      {pageTitle && (
        <h2 className="text-sm font-semibold uppercase tracking-widest mr-8">{pageTitle}</h2>
      )}

      <div className="flex-1 max-w-xl flex items-center gap-3 px-4 py-2 border border-[#DCDCD7] dark:border-[#303030] bg-[#FAFAF8] dark:bg-[#181818] rounded-none">
        <Search size={16} className="text-[#666666] dark:text-[#999999]" />
        <input
          type="text"
          placeholder="Search documents or ask a question..."
          className="flex-1 bg-transparent border-none outline-none text-sm placeholder-[#666666] dark:placeholder-[#999999]"
        />
        <div className="font-mono text-xs text-[#666666] dark:text-[#999999]">⌘K</div>
      </div>

      <div className="flex items-center gap-4 ml-6">
        <Settings size={18} className="text-[#666666] dark:text-[#999999]" />

        {/* Pill dark mode toggle */}
        <button
          onClick={() => setIsDarkMode(!isDarkMode)}
          className="relative w-14 h-7 rounded-full border border-[#DCDCD7] dark:border-[#303030] bg-[#FAFAF8] dark:bg-[#303030] transition-colors"
          aria-label="Toggle theme"
        >
          <div className={`absolute top-0.5 w-6 h-6 rounded-full bg-penny-text dark:bg-penny-dark-text transition-all duration-200 flex items-center justify-center ${
            isDarkMode ? 'left-[calc(100%-1.625rem)]' : 'left-0.5'
          }`}>
            {isDarkMode
              ? <Moon size={12} className="text-penny-dark-bg" />
              : <Sun size={12} className="text-penny-bg" />
            }
          </div>
        </button>

        {/* Vertical separator */}
        <div className="w-px h-8 bg-[#DCDCD7] dark:bg-[#303030]" />

        {/* User avatar + dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-8 h-8 bg-penny-text dark:bg-penny-dark-text text-penny-bg dark:text-penny-dark-bg flex items-center justify-center text-xs font-medium transition-opacity hover:opacity-80"
            aria-label="User menu"
          >
            {initials}
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-penny-surface dark:bg-penny-dark-surface border border-penny-border dark:border-penny-dark-border rounded-none shadow-sm z-50">
              {/* User info */}
              <div className="px-4 py-3 border-b border-penny-border dark:border-penny-dark-border">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-penny-text dark:bg-penny-dark-text text-penny-bg dark:text-penny-dark-bg flex items-center justify-center text-xs font-medium shrink-0">
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{user?.fullName || 'User'}</div>
                    <div className="text-[11px] text-[#666666] dark:text-[#999999] truncate">{user?.email || ''}</div>
                  </div>
                </div>
              </div>

              {/* Menu items */}
              <div className="py-1">
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-left text-[#666666] dark:text-[#999999] hover:bg-[#EDEDEA] dark:hover:bg-[#1a1a1a] transition-colors">
                  <UserIcon size={14} />
                  Profile
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-left text-[#666666] dark:text-[#999999] hover:bg-[#EDEDEA] dark:hover:bg-[#1a1a1a] transition-colors">
                  <Settings size={14} />
                  Settings
                </button>
              </div>

              {/* Sign out */}
              <div className="border-t border-penny-border dark:border-penny-dark-border py-1">
                <button
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-left text-penny-accent dark:text-penny-dark-accent hover:bg-[#EDEDEA] dark:hover:bg-[#1a1a1a] transition-colors"
                >
                  <LogOut size={14} />
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}