'use client';
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';
import { collectionsApi, studyApi, sourcesApi } from '@/lib/api';
import {
  BookOpen, FileText, ListChecks, ClipboardList, HelpCircle,
  Star, StickyNote, Loader2, Download, Copy, Check, ChevronDown,
  CheckCircle2, XCircle, RotateCcw, Lightbulb, Award
} from 'lucide-react';

const genTypes = [
  { type: 'short_summary', label: 'Short Summary', icon: FileText, desc: 'Key points in bullet format', color: 'from-blue-500 to-cyan-500' },
  { type: 'detailed_summary', label: 'Detailed Summary', icon: BookOpen, desc: 'Topic-wise explanations with definitions', color: 'from-purple-500 to-pink-500' },
  { type: 'short_answers', label: 'Short Answers', icon: ListChecks, desc: '2-5 mark exam questions', color: 'from-emerald-500 to-teal-500' },
  { type: 'long_answers', label: 'Long Answers', icon: ClipboardList, desc: '8-15 mark detailed answers', color: 'from-amber-500 to-orange-500' },
  { type: 'mcqs', label: 'MCQs', icon: HelpCircle, desc: 'Multiple choice with explanations', color: 'from-red-500 to-rose-500' },
  { type: 'important_questions', label: 'Important Questions', icon: Star, desc: 'Exam-oriented important questions', color: 'from-yellow-500 to-amber-500' },
  { type: 'notes', label: 'Chapter Notes', icon: StickyNote, desc: 'Organized chapter-wise notes', color: 'from-pink-500 to-rose-500' },
];

function InteractiveMCQCard({ item, index }: { item: any; index: number }) {
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [isChecked, setIsChecked] = useState(false);

  // Normalize options: supports string array or key-value object
  let rawOptions = item.options || [];
  if (rawOptions && !Array.isArray(rawOptions) && typeof rawOptions === 'object') {
    rawOptions = Object.entries(rawOptions).map(([k, v]) => `(${k}) ${v}`);
  }

  const parsedOptions = (rawOptions as string[]).map((opt: string, i: number) => {
    const trimmed = String(opt || '').trim();
    const match = trimmed.match(/^(?:\(([A-Da-d])\)|([A-Da-d])[\.\)]\s*)\s*(.*)/);
    let letter = String.fromCharCode(65 + i);
    let text = trimmed;
    if (match) {
      letter = (match[1] || match[2]).toUpperCase();
      text = match[3];
    }
    return { letter, text, raw: opt };
  });

  // Normalize correct answer
  const rawCorrect = String(item.correct_answer || item.answer || '').trim();
  const correctMatch = rawCorrect.match(/^(?:\(([A-Da-d])\)|([A-Da-d])[\.\)]\s*|\b([A-Da-d])\b)/);
  const correctLetter = correctMatch
    ? (correctMatch[1] || correctMatch[2] || correctMatch[3]).toUpperCase()
    : rawCorrect.toUpperCase();

  const isCorrect = selectedOption.toUpperCase() === correctLetter;

  const handleCheck = () => {
    if (!selectedOption) return;
    setIsChecked(true);
  };

  const handleReset = () => {
    setSelectedOption('');
    setIsChecked(false);
  };

  const questionText = item.question || item.statement || item.prompt || '';

  return (
    <div className="bg-white rounded-2xl border border-gray-200/90 p-5 shadow-sm space-y-4 transition-all">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs font-bold text-purple-700 bg-purple-50 px-2.5 py-1 rounded-lg border border-purple-100 flex-shrink-0">
          Question {index + 1} &bull; MCQ
        </span>
        {isChecked && (
          <span
            className={`text-xs font-bold px-2.5 py-1 rounded-lg flex items-center gap-1 ${
              isCorrect
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {isCorrect ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Correct</span>
              </>
            ) : (
              <>
                <XCircle className="w-3.5 h-3.5 text-red-600" />
                <span>Incorrect</span>
              </>
            )}
          </span>
        )}
      </div>

      {/* Question Statement */}
      <div className="text-sm font-semibold text-gray-900 leading-relaxed">
        <MarkdownRenderer content={questionText} />
      </div>

      {/* Interactive Radio Options */}
      <div className="space-y-2.5">
        {parsedOptions.map((opt: any) => {
          const isSelected = selectedOption === opt.letter;
          let containerClass = "border-gray-200 hover:border-purple-300 hover:bg-gray-50/50";
          let badgeClass = "bg-gray-100 text-gray-600 border-gray-200";

          if (isChecked) {
            if (opt.letter === correctLetter) {
              containerClass = "border-emerald-500 bg-emerald-50/60 text-emerald-950 ring-1 ring-emerald-500";
              badgeClass = "bg-emerald-600 text-white border-emerald-600";
            } else if (isSelected && !isCorrect) {
              containerClass = "border-red-500 bg-red-50/60 text-red-950 ring-1 ring-red-500";
              badgeClass = "bg-red-600 text-white border-red-600";
            } else {
              containerClass = "border-gray-200 opacity-60";
              badgeClass = "bg-gray-100 text-gray-400 border-gray-200";
            }
          } else if (isSelected) {
            containerClass = "border-purple-600 bg-purple-50/40 text-purple-950 ring-1 ring-purple-600";
            badgeClass = "bg-purple-600 text-white border-purple-600";
          }

          return (
            <label
              key={opt.letter}
              htmlFor={`study_mcq_${index}_${opt.letter}`}
              className={`flex items-center gap-3 p-3.5 rounded-xl border text-sm cursor-pointer transition-all ${containerClass}`}
            >
              <input
                type="radio"
                id={`study_mcq_${index}_${opt.letter}`}
                name={`study_mcq_group_${index}`}
                value={opt.letter}
                checked={isSelected}
                onChange={() => !isChecked && setSelectedOption(opt.letter)}
                disabled={isChecked}
                className="w-4 h-4 text-purple-600 border-gray-300 focus:ring-purple-500 cursor-pointer"
              />
              <span className={`w-6 h-6 rounded-lg text-xs font-bold flex items-center justify-center border flex-shrink-0 ${badgeClass}`}>
                {opt.letter}
              </span>
              <span className="flex-1 font-medium text-gray-800">{opt.text || opt.raw}</span>
            </label>
          );
        })}
      </div>

      {/* Buttons */}
      <div className="flex flex-wrap items-center gap-3 pt-1">
        {!isChecked ? (
          <button
            onClick={handleCheck}
            disabled={!selectedOption}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Check Answer</span>
          </button>
        ) : (
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Try Again / Reset</span>
          </button>
        )}
      </div>

      {/* Feedback & Explanation */}
      {isChecked && (
        <div
          className={`p-4 rounded-xl border space-y-2 animate-in fade-in duration-200 ${
            isCorrect
              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
              : 'bg-amber-50/70 border-amber-200 text-amber-900'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider">
              {isCorrect ? '✓ Well Done!' : '✗ Not Quite'}
            </span>
            <span className="text-xs font-medium">
              &bull; Correct answer is <b>Option {correctLetter}</b>
            </span>
          </div>
          {item.explanation && (
            <div className="text-xs text-gray-700 leading-relaxed bg-white/70 p-2.5 rounded-lg border border-gray-100">
              <span className="font-bold">Explanation: </span>
              <MarkdownRenderer content={item.explanation} className="inline" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

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
    let inner = content?.content || content?.raw || content;

    // 1. Try parsing JSON if inner is a string containing JSON or code blocks
    if (typeof inner === 'string') {
      const cleanStr = inner.trim();
      let candidate = cleanStr;
      if (candidate.includes('```json')) {
        candidate = candidate.split('```json')[1].split('```')[0].trim();
      } else if (candidate.includes('```')) {
        candidate = candidate.split('```')[1].split('```')[0].trim();
      }
      if (candidate.startsWith('[') || candidate.startsWith('{')) {
        try {
          const parsed = JSON.parse(candidate);
          inner = Array.isArray(parsed) ? parsed : (parsed.questions || parsed.items || parsed);
        } catch (e) {
          // Keep as string
        }
      }
    }

    // 2. If it is a string (Short Summary, Detailed Summary, Notes, etc.)
    if (typeof inner === 'string') {
      if (resultType === 'short_summary') {
        return (
          <div className="bg-white rounded-2xl border border-blue-100 shadow-sm overflow-hidden">
            <div className="px-6 py-4 bg-gradient-to-r from-blue-500/10 via-cyan-500/10 to-transparent border-b border-blue-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-500 text-white flex items-center justify-center shadow-sm">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Executive Short Summary</h3>
                  <p className="text-xs text-blue-600 font-medium">Core Takeaways & High-Yield Revision Points</p>
                </div>
              </div>
              <span className="text-xs bg-blue-100 text-blue-700 font-bold px-2.5 py-0.5 rounded-full">
                Summary Note
              </span>
            </div>
            <div className="p-6">
              <MarkdownRenderer content={inner} />
            </div>
          </div>
        );
      }

      if (resultType === 'detailed_summary') {
        return (
          <div className="bg-white rounded-2xl border border-purple-100 shadow-sm overflow-hidden">
            <div className="px-6 py-4 bg-gradient-to-r from-purple-500/10 via-pink-500/10 to-transparent border-b border-purple-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center shadow-sm">
                  <BookOpen className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Comprehensive Detailed Summary</h3>
                  <p className="text-xs text-purple-600 font-medium">In-Depth Concepts, Definitions & Core Explanations</p>
                </div>
              </div>
              <span className="text-xs bg-purple-100 text-purple-700 font-bold px-2.5 py-0.5 rounded-full">
                In-Depth Study
              </span>
            </div>
            <div className="p-6">
              <MarkdownRenderer content={inner} />
            </div>
          </div>
        );
      }

      if (resultType === 'notes') {
        return (
          <div className="bg-white rounded-2xl border border-pink-100 shadow-sm overflow-hidden">
            <div className="px-6 py-4 bg-gradient-to-r from-pink-500/10 via-rose-500/10 to-transparent border-b border-pink-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-pink-500 text-white flex items-center justify-center shadow-sm">
                  <StickyNote className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Structured Chapter Notes</h3>
                  <p className="text-xs text-pink-600 font-medium">Topic-wise Concepts, Formulas & Review Points</p>
                </div>
              </div>
              <span className="text-xs bg-pink-100 text-pink-700 font-bold px-2.5 py-0.5 rounded-full">
                Revision Notes
              </span>
            </div>
            <div className="p-6">
              <MarkdownRenderer content={inner} />
            </div>
          </div>
        );
      }

      // Default string fallback rendered with MarkdownRenderer
      return (
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
          <MarkdownRenderer content={inner} />
        </div>
      );
    }

    // 3. If it is an Array of questions / MCQs
    if (Array.isArray(inner)) {
      return (
        <div className="space-y-4">
          {inner.map((item: any, i: number) => {
            if (item.options && Array.isArray(item.options)) {
              return <InteractiveMCQCard key={i} item={item} index={i} />;
            }
            return (
              <div key={i} className="bg-white rounded-2xl p-5 border border-gray-200/80 shadow-sm space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-bold text-purple-700 bg-purple-50 px-2.5 py-1 rounded-lg border border-purple-100">
                    Question {i + 1}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {item.marks && (
                      <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md">
                        {item.marks} Mark{item.marks > 1 ? 's' : ''}
                      </span>
                    )}
                    {item.importance && (
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-md ${
                        item.importance === 'Very Important'
                          ? 'bg-red-50 text-red-600 border border-red-200'
                          : 'bg-blue-50 text-blue-600 border border-blue-200'
                      }`}>
                        {item.importance}
                      </span>
                    )}
                  </div>
                </div>

                {item.question && (
                  <p className="font-semibold text-gray-900 text-sm leading-relaxed">
                    {item.question}
                  </p>
                )}

                {item.answer && (
                  <div className="bg-gray-50/80 rounded-xl p-3.5 border border-gray-100 text-sm">
                    <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1.5">Answer:</p>
                    <MarkdownRenderer content={item.answer} />
                  </div>
                )}

                {item.explanation && (
                  <div className="bg-amber-50/60 rounded-xl p-3 border border-amber-100 text-xs text-amber-900 flex items-start gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Key Insight: </span>
                      {item.explanation}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      );
    }

    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
        <pre className="text-xs text-gray-600 whitespace-pre-wrap">{JSON.stringify(inner, null, 2)}</pre>
      </div>
    );
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
