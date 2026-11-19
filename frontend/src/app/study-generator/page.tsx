'use client';
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, studyApi, sourcesApi } from '@/lib/api';
import {
  BookOpen, FileText, ListChecks, ClipboardList, HelpCircle,
  Star, Layers, StickyNote, Loader2, Download, Copy, Check, ChevronDown
} from 'lucide-react';

const genTypes = [
  { type: 'short_summary', label: 'Short Summary', icon: FileText, desc: 'Key points in bullet format', color: 'from-blue-500 to-cyan-500' },
  { type: 'detailed_summary', label: 'Detailed Summary', icon: BookOpen, desc: 'Topic-wise explanations with definitions', color: 'from-purple-500 to-pink-500' },
  { type: 'short_answers', label: 'Short Answers', icon: ListChecks, desc: '2-5 mark exam questions', color: 'from-emerald-500 to-teal-500' },
  { type: 'long_answers', label: 'Long Answers', icon: ClipboardList, desc: '8-15 mark detailed answers', color: 'from-amber-500 to-orange-500' },
  { type: 'mcqs', label: 'MCQs', icon: HelpCircle, desc: 'Multiple choice with explanations', color: 'from-red-500 to-rose-500' },
  { type: 'important_questions', label: 'Important Questions', icon: Star, desc: 'Exam-oriented important questions', color: 'from-yellow-500 to-amber-500' },
  { type: 'flashcards', label: 'Flashcards', icon: Layers, desc: 'Quick revision Q&A cards', color: 'from-indigo-500 to-violet-500' },
  { type: 'notes', label: 'Chapter Notes', icon: StickyNote, desc: 'Organized chapter-wise notes', color: 'from-pink-500 to-rose-500' },
];

export default function StudyGeneratorPage() {
  const searchParams = useSearchParams();
  const presetCol = searchParams.get('collection');
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSources, setSelectedSources] = useState<number[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [resultType, setResultType] = useState('');
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    collectionsApi.list().then((c: any[]) => {
      setCollections(c);
      if (presetCol) setSelectedCol(Number(presetCol));
      else if (c.length) setSelectedCol(c[0].id);
    });
  }, [presetCol]);

  useEffect(() => {
    if (!selectedCol) return;
    sourcesApi.list(selectedCol).then((s: any[]) => {
      setSources(s.filter((x: any) => x.status === 'completed'));
      setSelectedSources([]);
    });
    studyApi.listGenerated(selectedCol).then(setHistory).catch(() => setHistory([]));
  }, [selectedCol]);

  const generate = async (type: string) => {
    if (!selectedCol) return;
    setGenerating(type);
    setResult(null);
    try {
      const srcIds = selectedSources.length > 0 ? selectedSources : undefined;
      const r = await studyApi.generate(selectedCol, type, srcIds);
      setResult(r);
      setResultType(type);
      studyApi.listGenerated(selectedCol).then(setHistory).catch(() => {});
    } catch (e: any) {
      alert(e.message || 'Generation failed');
    } finally {
      setGenerating(null);
    }
  };

  const toggleSource = (id: number) => {
    setSelectedSources((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const copyContent = () => {
    const text = typeof result?.content_json === 'string'
      ? result.content_json
      : JSON.stringify(result?.content_json, null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderContent = (data: any) => {
    if (!data) return null;
    const content = data.content_json || data;
    const inner = content?.content || content?.raw || content;

    if (typeof inner === 'string') {
      return <div className="prose prose-sm max-w-none whitespace-pre-wrap text-gray-700 leading-relaxed">{inner}</div>;
    }
    if (Array.isArray(inner)) {
      return (
        <div className="space-y-4">
          {inner.map((item: any, i: number) => (
            <div key={i} className="bg-gray-50 rounded-xl p-4 border border-gray-100">
              {item.question && <p className="font-medium text-gray-900 mb-2">Q: {item.question}</p>}
              {item.answer && <p className="text-gray-600 text-sm">A: {item.answer}</p>}
              {item.correct_answer && <p className="text-emerald-600 text-sm font-medium mt-1">Correct: {item.correct_answer}</p>}
              {item.options && (
                <div className="mt-2 space-y-1">
                  {item.options.map((o: string, j: number) => (
                    <p key={j} className="text-sm text-gray-600 pl-4">{o}</p>
                  ))}
                </div>
              )}
              {item.explanation && <p className="text-gray-500 text-xs mt-2 italic">💡 {item.explanation}</p>}
              {item.importance && <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full ${item.importance === 'Very Important' ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>{item.importance}</span>}
            </div>
          ))}
        </div>
      );
    }
    return <pre className="text-sm text-gray-600 whitespace-pre-wrap">{JSON.stringify(inner, null, 2)}</pre>;
  };

  return (
    <DashboardLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Study Generator</h1>
        <p className="text-gray-500 text-sm mt-1">Generate study materials from your uploaded content</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Config */}
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <label className="block text-sm font-medium text-gray-700 mb-2">Collection</label>
            <select value={selectedCol} onChange={(e) => setSelectedCol(Number(e.target.value))}
              className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
              <option value={0}>Select Collection</option>
              {collections.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          {sources.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 p-5">
              <label className="block text-sm font-medium text-gray-700 mb-2">Sources ({selectedSources.length ? `${selectedSources.length} selected` : 'All'})</label>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {sources.map((s: any) => (
                  <label key={s.id} className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                    <input type="checkbox" checked={selectedSources.includes(s.id)} onChange={() => toggleSource(s.id)}
                      className="w-4 h-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500" />
                    <span className="text-sm text-gray-700 truncate">{s.original_filename || s.url}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Generation Options */}
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <label className="block text-sm font-medium text-gray-700 mb-3">Generate</label>
            <div className="space-y-2">
              {genTypes.map((g) => (
                <button key={g.type} onClick={() => generate(g.type)} disabled={!selectedCol || generating !== null}
                  className="w-full flex items-center gap-3 p-3 rounded-xl border border-gray-100 hover:border-purple-200 hover:bg-purple-50/50 transition-all text-left disabled:opacity-50 group">
                  <div className={`w-9 h-9 bg-gradient-to-br ${g.color} rounded-lg flex items-center justify-center flex-shrink-0`}>
                    <g.icon className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900">{g.label}</div>
                    <div className="text-xs text-gray-400">{g.desc}</div>
                  </div>
                  {generating === g.type && <Loader2 className="w-4 h-4 animate-spin text-purple-500" />}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Output */}
        <div className="lg:col-span-2">
          {generating && (
            <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
              <Loader2 className="w-10 h-10 mx-auto text-purple-500 animate-spin mb-4" />
              <p className="text-gray-500">Generating {genTypes.find((g) => g.type === generating)?.label}...</p>
              <p className="text-xs text-gray-400 mt-1">This may take a moment</p>
            </div>
          )}

          {!generating && result && (
            <div className="bg-white rounded-2xl border border-gray-100">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-900">{result.title || resultType}</h3>
                <div className="flex gap-2">
                  <button onClick={copyContent} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-50 rounded-lg hover:bg-gray-100">
                    {copied ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
                  </button>
                </div>
              </div>
              <div className="p-6 max-h-[calc(100vh-16rem)] overflow-y-auto">
                {renderContent(result)}
              </div>
            </div>
          )}

          {!generating && !result && (
            <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
              <BookOpen className="w-12 h-12 mx-auto text-gray-200 mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">Select a generation type</h3>
              <p className="text-gray-400 text-sm">Choose a collection and click any generation option to create study materials</p>
            </div>
          )}

          {/* History */}
          {history.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 mt-4 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Recent Generations</h3>
              <div className="space-y-2">
                {history.slice(0, 5).map((h: any) => (
                  <button key={h.id} onClick={() => { setResult(h); setResultType(h.content_type); }}
                    className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 text-left">
                    <BookOpen className="w-4 h-4 text-purple-500" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">{h.title}</div>
                      <div className="text-xs text-gray-400">{new Date(h.created_at).toLocaleDateString()}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
