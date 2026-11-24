'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, FolderOpen, MessageSquare, BookOpen,
  GitCompareArrows, ClipboardCheck, Layers,
  Settings, ChevronLeft, ChevronRight, LogOut, Brain
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const primaryNav = [
  { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/chat', icon: MessageSquare, label: 'AI Chat Assistant' },
  { href: '/collections', icon: FolderOpen, label: 'Study Resources' },
  { href: '/duplicate-detector', icon: GitCompareArrows, label: 'Duplicate Detector' },
];

const toolsNav = [
  { href: '/study-generator', icon: BookOpen, label: 'Study Generator' },
  { href: '/quiz', icon: ClipboardCheck, label: 'Quiz & Practice' },
  { href: '/flashcards', icon: Layers, label: 'Flashcards' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const renderLink = (item: { href: string; icon: any; label: string; badge?: string }) => {
    const active = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href + '/'));
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 relative group
          ${active
            ? 'bg-purple-50 text-purple-700 font-semibold shadow-sm'
            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
          }
        `}
      >
        <item.icon className={`w-[18px] h-[18px] flex-shrink-0 ${active ? 'text-purple-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
        {!collapsed && (
          <div className="flex items-center justify-between flex-1 min-w-0">
            <span className="truncate">{item.label}</span>
            {item.badge && (
              <span className="text-[10px] font-bold uppercase tracking-wider bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-1.5 py-0.5 rounded-md">
                {item.badge}
              </span>
            )}
          </div>
        )}
      </Link>
    );
  };

  return (
    <aside className={`fixed left-0 top-0 h-full bg-white border-r border-gray-200 flex flex-col z-40 transition-all duration-300 ${collapsed ? 'w-[68px]' : 'w-[260px]'}`}>
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-100">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm shadow-purple-200">
            <Brain className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div>
              <h1 className="font-bold text-gray-900 text-base leading-tight tracking-tight">Source2Study</h1>
              <p className="text-[10px] font-medium text-gray-400">AI Study Platform</p>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-4 px-2 space-y-5 overflow-y-auto">
        <div className="space-y-0.5">
          {!collapsed && (
            <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
              Workspace
            </div>
          )}
          {primaryNav.map(renderLink)}
        </div>

        <div className="space-y-0.5 pt-2 border-t border-gray-100">
          {!collapsed && (
            <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
              Study Tools
            </div>
          )}
          {toolsNav.map(renderLink)}
        </div>

        <div className="space-y-0.5 pt-2 border-t border-gray-100">
          {renderLink({ href: '/settings', icon: Settings, label: 'Settings' })}
        </div>
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:shadow-sm"
        aria-label="Toggle sidebar"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>

      {/* User Footer */}
      <div className="border-t border-gray-100 p-3">
        <div className="flex items-center gap-3 px-2 py-1.5 rounded-xl hover:bg-gray-50 transition-colors">
          <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {user?.full_name?.[0]?.toUpperCase() || 'U'}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">{user?.full_name || 'User'}</p>
              <p className="text-xs text-gray-400 truncate">{user?.email || ''}</p>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={logout}
              className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
