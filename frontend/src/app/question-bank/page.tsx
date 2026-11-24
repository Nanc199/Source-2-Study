'use client';
import React, { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, questionsApi } from '@/lib/api';
import { Database, Search, FileText, Copy, Check } from 'lucide-react';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';

export default function QuestionBankPage() {
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [copied, setCopied] = useState<number | null>(null);

  useEffect(() => {
    collectionsApi.list().then((c: any[]) => {
      setCollections(c);
      if (c.length) setSelectedCol(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedCol) return;
    setLoading(true);
    const params: Record<string, string> = {};
    if (search) params.search = search;
    questionsApi.getQuestions(selectedCol, params).then(setQuestions).catch(() => setQuestions([])).finally(() => setLoading(false));
  }, [selectedCol]);

  const doSearch = () => {
    if (!selectedCol) return;
    setLoading(true);
    const params: Record<string, string> = {};
    if (search) params.search = search;
    questionsApi.getQuestions(selectedCol, params).then(setQuestions).catch(() => setQuestions([])).finally(() => setLoading(false));
  };

  const copyQ = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <DashboardLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Question Bank</h1>
        <p className="text-gray-500 text-sm mt-1">All extracted questions from your documents</p>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select value={selectedCol} onChange={(e) => setSelectedCol(Number(e.target.value))}
          className="px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 min-w-[200px]">
          <option value={0}>Select Collection</option>
          {collections.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && doSearch()}
            placeholder="Search questions..." className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
        </div>
        <span className="text-sm text-gray-400">{questions.length} questions</span>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full border-4 border-gray-200 border-t-purple-600 h-10 w-10" /></div>
      ) : questions.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-16 text-center">
          <Database className="w-16 h-16 mx-auto text-gray-200 mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No questions extracted</h3>
          <p className="text-gray-400 text-sm">Upload question papers and run duplicate detection to extract questions</p>
        </div>
      ) : (
        <div className="space-y-2">
          {questions.map((q: any) => (
            <div key={q.id} className="bg-white rounded-xl border border-gray-100 p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <div className="text-sm text-gray-900 leading-relaxed">
                    <MarkdownRenderer content={q.question_text || ''} />
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-400 flex-wrap">
                    <span className="flex items-center gap-1"><FileText className="w-3 h-3" /> {q.source_filename || 'Unknown'}</span>
                    {q.year && <span className="bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full">{q.year}</span>}
                    {q.page_number && <span>Page {q.page_number}</span>}
                    {q.question_type && <span className="bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{q.question_type}</span>}
                  </div>
                </div>
                <button onClick={() => copyQ(q.question_text, q.id)} className="p-2 hover:bg-gray-50 rounded-lg text-gray-400 hover:text-gray-600">
                  {copied === q.id ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
