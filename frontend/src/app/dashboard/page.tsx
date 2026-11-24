'use client';
import React, { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { dashboardApi, collectionsApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import Link from 'next/link';
import {
  FileText, FolderOpen, HelpCircle, ClipboardCheck,
  MessageSquare, Sparkles, GitCompareArrows, ArrowRight,
  Clock, Plus, CheckCircle2, BookOpen
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
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

  const statMetrics = [
    { label: 'Study Resources', value: stats?.total_sources || 0, icon: FileText, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'Collections', value: stats?.total_collections || 0, icon: FolderOpen, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Indexed Questions', value: stats?.total_questions || 0, icon: HelpCircle, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Quizzes Taken', value: stats?.total_quizzes || 0, icon: ClipboardCheck, color: 'text-amber-600', bg: 'bg-amber-50' },
  ];

  return (
    <DashboardLayout>
      {/* Header Banner */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight">
          Welcome back, {user?.full_name?.split(' ')[0] || 'Student'}
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Your centralized AI study command center. Query your materials, find recurring exam questions, and generate study resources.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {statMetrics.map((item) => (
          <div key={item.label} className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{item.label}</span>
              <div className={`w-8 h-8 ${item.bg} rounded-xl flex items-center justify-center`}>
                <item.icon className={`w-4 h-4 ${item.color}`} />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900">{loading ? '...' : item.value}</div>
          </div>
        ))}
      </div>

      {/* Primary Feature Workspaces */}
      <div className="mb-8">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Core Workspaces</h2>
        <div className="grid md:grid-cols-3 gap-5">
          {/* AI Chat Workspace */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow">
            <div>
              <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-4">
                <MessageSquare className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-gray-900 text-base mb-1.5">AI Chat Assistant</h3>
              <p className="text-xs text-gray-500 leading-relaxed mb-4">
                Engage in conversational Q&A with your documents. Get accurate, verified answers backed by source citations.
              </p>
            </div>
            <Link
              href="/chat"
              className="inline-flex items-center justify-between px-4 py-2.5 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold rounded-xl transition-colors"
            >
              <span>Start Asking Questions</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Duplicate Detector Workspace */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div>
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
                <GitCompareArrows className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-gray-900 text-base mb-1.5">Duplicate Question Detector</h3>
              <p className="text-xs text-gray-500 leading-relaxed mb-4">
                Upload past-year question papers (PDF, scanned, images). Identify repeated exam questions and download consolidated question banks.
              </p>
            </div>
            <Link
              href="/duplicate-detector"
              className="inline-flex items-center justify-between px-4 py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-xl transition-colors"
            >
              <span>Analyze Question Papers</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Study Resources Workspace */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow">
            <div>
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
                <FolderOpen className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-gray-900 text-base mb-1.5">Study Resources</h3>
              <p className="text-xs text-gray-500 leading-relaxed mb-4">
                Upload PDFs, DOCX, presentation slides, images, website links, or YouTube videos organized by subjects.
              </p>
            </div>
            <Link
              href="/collections"
              className="inline-flex items-center justify-between px-4 py-2.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-xl transition-colors"
            >
              <span>View & Upload Resources</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Two-Column Section: Collections & Activity */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Collections Overview */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold text-gray-900 text-base">Your Study Collections</h2>
              <p className="text-xs text-gray-500 mt-0.5">Organized folders of course materials</p>
            </div>
            <Link
              href="/collections"
              className="text-xs font-semibold text-purple-600 hover:text-purple-700"
            >
              View all ({collections.length}) &rarr;
            </Link>
          </div>

          {collections.length === 0 ? (
            <div className="text-center py-10 border border-dashed border-gray-200 rounded-xl">
              <FolderOpen className="w-10 h-10 mx-auto text-gray-300 mb-2" />
              <p className="text-sm font-medium text-gray-700">No collections created yet</p>
              <p className="text-xs text-gray-400 mt-1 mb-4">Create your first subject collection to start uploading papers and materials.</p>
              <Link
                href="/collections"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-medium hover:bg-purple-700"
              >
                <Plus className="w-3.5 h-3.5" /> Create Collection
              </Link>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-3">
              {collections.slice(0, 4).map((c: any) => (
                <Link
                  key={c.id}
                  href={`/collections/${c.id}`}
                  className="p-4 rounded-xl border border-gray-100 hover:border-purple-200 hover:bg-purple-50/30 transition-all group flex items-start gap-3"
                >
                  <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                    <BookOpen className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-900 truncate group-hover:text-purple-700">
                      {c.name}
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5 truncate">
                      {c.source_count || 0} source documents
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity Log */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
          <h2 className="font-semibold text-gray-900 text-base mb-1">Recent Activity</h2>
          <p className="text-xs text-gray-500 mb-4">Your latest actions and updates</p>

          {activity.length === 0 ? (
            <div className="text-center py-10 text-gray-400">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-xs">No recent actions recorded.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {activity.slice(0, 6).map((item: any, idx: number) => (
                <div key={idx} className="py-2.5 flex items-start gap-2.5 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-800 font-medium truncate">{item.title}</p>
                    <p className="text-[11px] text-gray-400 mt-0.5">
                      {new Date(item.timestamp).toLocaleDateString()}
                    </p>
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
