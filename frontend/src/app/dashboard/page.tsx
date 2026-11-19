'use client';
import React, { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { dashboardApi, collectionsApi } from '@/lib/api';
import Link from 'next/link';
import {
  FileText, FolderOpen, HelpCircle, ClipboardCheck,
  Upload, MessageSquare, Sparkles, ArrowRight, Clock
} from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [collections, setCollections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      dashboardApi.stats().catch(() => null),
      dashboardApi.recentActivity().catch(() => []),
      collectionsApi.list().catch(() => []),
    ]).then(([s, a, c]) => {
      setStats(s);
      setActivity(a || []);
      setCollections(c || []);
    }).finally(() => setLoading(false));
  }, []);

  const statCards = [
    { label: 'Total Sources', value: stats?.total_sources || 0, icon: FileText, color: 'bg-blue-50 text-blue-600', iconBg: 'bg-blue-100' },
    { label: 'Collections', value: stats?.total_collections || 0, icon: FolderOpen, color: 'bg-purple-50 text-purple-600', iconBg: 'bg-purple-100' },
    { label: 'Questions Extracted', value: stats?.total_questions || 0, icon: HelpCircle, color: 'bg-emerald-50 text-emerald-600', iconBg: 'bg-emerald-100' },
    { label: 'Quizzes Completed', value: stats?.total_quizzes || 0, icon: ClipboardCheck, color: 'bg-amber-50 text-amber-600', iconBg: 'bg-amber-100' },
  ];

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Welcome back! Here's your learning overview.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        {statCards.map((s) => (
          <div key={s.label} className="bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className={`w-10 h-10 ${s.iconBg} rounded-xl flex items-center justify-center`}>
                <s.icon className={`w-5 h-5 ${s.color.split(' ')[1]}`} />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900">{s.value}</div>
            <div className="text-sm text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            {[
              { href: '/collections', icon: Upload, label: 'Upload Sources', desc: 'Add new study materials', color: 'text-purple-600 bg-purple-50' },
              { href: '/chat', icon: MessageSquare, label: 'Start AI Chat', desc: 'Ask about your docs', color: 'text-blue-600 bg-blue-50' },
              { href: '/quiz', icon: ClipboardCheck, label: 'Take a Quiz', desc: 'Test your knowledge', color: 'text-emerald-600 bg-emerald-50' },
              { href: '/duplicate-detector', icon: Sparkles, label: 'Detect Duplicates', desc: 'Analyze question papers', color: 'text-amber-600 bg-amber-50' },
            ].map((a) => (
              <Link key={a.href} href={a.href} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors group">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${a.color}`}>
                  <a.icon className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">{a.label}</div>
                  <div className="text-xs text-gray-400">{a.desc}</div>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors" />
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Collections */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Collections</h2>
            <Link href="/collections" className="text-xs text-purple-600 font-medium hover:text-purple-700">View all</Link>
          </div>
          {collections.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <FolderOpen className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No collections yet</p>
              <Link href="/collections" className="text-purple-600 text-sm font-medium mt-2 inline-block">Create one →</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {collections.slice(0, 5).map((c: any) => (
                <Link key={c.id} href={`/collections/${c.id}`} className="block p-3 rounded-xl hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center">
                      <FolderOpen className="w-4 h-4 text-purple-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">{c.name}</div>
                      <div className="text-xs text-gray-400">{c.source_count || 0} sources</div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
          {activity.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Clock className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No recent activity</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activity.slice(0, 8).map((a: any, i: number) => (
                <div key={i} className="flex items-start gap-3 py-2">
                  <div className="w-2 h-2 bg-purple-400 rounded-full mt-1.5 flex-shrink-0" />
                  <div>
                    <div className="text-sm text-gray-700">{a.title}</div>
                    <div className="text-xs text-gray-400">{a.collection_name && `${a.collection_name} · `}{new Date(a.timestamp).toLocaleDateString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
