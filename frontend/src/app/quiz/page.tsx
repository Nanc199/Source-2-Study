'use client';
import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, quizApi } from '@/lib/api';
import { ClipboardCheck, Loader2, Clock, CheckCircle2, XCircle, ChevronLeft, ChevronRight, Trophy, RotateCcw } from 'lucide-react';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';

type Phase = 'setup' | 'quiz' | 'results';

export default function QuizPage() {
  const searchParams = useSearchParams();
  const presetCol = searchParams.get('collection');
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [phase, setPhase] = useState<Phase>('setup');
  // Setup
  const [questionCount, setQuestionCount] = useState(10);
  const [difficulty, setDifficulty] = useState('medium');
  const [qType, setQType] = useState('mcq');
  const [generating, setGenerating] = useState(false);
  // Quiz
  const [questions, setQuestions] = useState<any[]>([]);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [timeLeft, setTimeLeft] = useState(0);
  const [timerEnabled, setTimerEnabled] = useState(true);
  const [timeLimit, setTimeLimit] = useState(15);
  // Results
  const [results, setResults] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    collectionsApi.list().then((c: any[]) => {
      setCollections(c);
      if (presetCol) setSelectedCol(Number(presetCol));
      else if (c.length) setSelectedCol(c[0].id);
    });
  }, [presetCol]);

  // Timer
  useEffect(() => {
    if (phase !== 'quiz' || !timerEnabled || timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) { handleSubmit(); return 0; }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [phase, timerEnabled, timeLeft]);

  const startQuiz = async () => {
    if (!selectedCol) return;
    setGenerating(true);
    try {
      const qs = await quizApi.generate(selectedCol, { question_count: questionCount, difficulty, question_type: qType });
      if (Array.isArray(qs)) {
        setQuestions(qs);
        setAnswers({});
        setCurrentQ(0);
        setTimeLeft(timerEnabled ? timeLimit * 60 : 0);
        setPhase('quiz');
      } else {
        alert('Failed to generate quiz. Make sure you have processed documents and a valid API key.');
      }
    } catch (e: any) { alert(e.message); }
    finally { setGenerating(false); }
  };

  const selectAnswer = (qId: number, answer: string) => {
    setAnswers((prev) => ({ ...prev, [qId]: answer }));
  };

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const answersArr = questions.map((q: any) => ({
        question_id: q.id,
        selected_answer: answers[q.id] || '',
      }));
      const timeTaken = timerEnabled ? (timeLimit * 60 - timeLeft) : undefined;
      const result = await quizApi.submit({
        collection_id: selectedCol,
        title: `${difficulty} ${qType} Quiz`,
        difficulty,
        questions_json: questions,
        answers_json: answersArr,
        time_taken_seconds: timeTaken,
      });
      setResults(result);
      setPhase('results');
    } catch (e: any) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  const formatTime = (s: number) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  const answeredCount = Object.keys(answers).length;

  if (phase === 'quiz' && questions.length > 0) {
    const q = questions[currentQ];
    return (
      <DashboardLayout>
        {/* Quiz Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Question {currentQ + 1} of {questions.length}</h1>
            <div className="w-48 h-1.5 bg-gray-100 rounded-full mt-2">
              <div className="h-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full transition-all" style={{ width: `${((currentQ + 1) / questions.length) * 100}%` }} />
            </div>
          </div>
          {timerEnabled && (
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl font-mono text-lg font-bold ${timeLeft <= 60 ? 'bg-red-50 text-red-600' : 'bg-gray-50 text-gray-700'}`}>
              <Clock className="w-5 h-5" /> {formatTime(timeLeft)}
            </div>
          )}
        </div>

        {/* Question Nav */}
        <div className="flex flex-wrap gap-2 mb-6">
          {questions.map((_: any, i: number) => (
            <button key={i} onClick={() => setCurrentQ(i)}
              className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                i === currentQ ? 'bg-purple-600 text-white' :
                answers[questions[i].id] ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' :
                'bg-gray-50 text-gray-500 border border-gray-200'
              }`}>
              {i + 1}
            </button>
          ))}
        </div>

        {/* Question Card */}
        <div className="bg-white rounded-2xl border border-gray-100 p-8 mb-6">
          <div className="text-lg font-medium text-gray-900 mb-6 leading-relaxed">
            <MarkdownRenderer content={q.question || ''} />
          </div>
          <div className="space-y-3">
            {(q.options || []).map((opt: string, i: number) => {
              const trimmed = opt.trim();
              const match = trimmed.match(/^(?:\(([A-Da-d])\)|([A-Da-d])[\.\)]\s*)\s*(.*)/);
              let letter = String.fromCharCode(65 + i);
              let cleanText = trimmed;
              if (match) {
                letter = (match[1] || match[2]).toUpperCase();
                cleanText = match[3];
              } else if (trimmed.startsWith('A') || trimmed.startsWith('B') || trimmed.startsWith('C') || trimmed.startsWith('D')) {
                letter = trimmed.charAt(0).toUpperCase();
              }
              const isSelected = answers[q.id] === letter;
              return (
                <label
                  key={i}
                  htmlFor={`quiz_q_${q.id}_opt_${letter}`}
                  className={`w-full flex items-center justify-between p-4 rounded-xl border-2 transition-all cursor-pointer ${
                    isSelected
                      ? 'border-purple-600 bg-purple-50/50 shadow-sm ring-1 ring-purple-600'
                      : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50/70 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-3.5 flex-1">
                    <input
                      type="radio"
                      id={`quiz_q_${q.id}_opt_${letter}`}
                      name={`quiz_radio_group_${q.id}`}
                      value={letter}
                      checked={isSelected}
                      onChange={() => selectAnswer(q.id, letter)}
                      className="w-4 h-4 text-purple-600 border-gray-300 focus:ring-purple-500 cursor-pointer"
                    />
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 transition-colors ${
                        isSelected
                          ? 'bg-purple-600 text-white shadow-sm'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {letter}
                    </div>
                    <span className="text-sm font-medium text-gray-800 leading-relaxed">
                      {cleanText || opt}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-gray-400 pl-2">Option {letter}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Nav Buttons */}
        <div className="flex items-center justify-between">
          <button onClick={() => setCurrentQ(Math.max(0, currentQ - 1))} disabled={currentQ === 0}
            className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          <span className="text-sm text-gray-400">{answeredCount}/{questions.length} answered</span>
          {currentQ < questions.length - 1 ? (
            <button onClick={() => setCurrentQ(currentQ + 1)}
              className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-xl text-sm font-medium hover:bg-purple-700">
              Next <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button onClick={handleSubmit} disabled={submitting}
              className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl text-sm font-bold shadow-lg">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Submit Quiz
            </button>
          )}
        </div>
      </DashboardLayout>
    );
  }

  if (phase === 'results' && results) {
    const score = results.score || 0;
    const total = results.total_marks || 1;
    const pct = Math.round((score / total) * 100);
    const answersData = results.answers_json || [];
    return (
      <DashboardLayout>
        <div className="max-w-3xl mx-auto">
          <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center mb-6">
            <div className={`w-24 h-24 mx-auto rounded-full flex items-center justify-center mb-4 ${pct >= 70 ? 'bg-emerald-50' : pct >= 40 ? 'bg-amber-50' : 'bg-red-50'}`}>
              <Trophy className={`w-10 h-10 ${pct >= 70 ? 'text-emerald-500' : pct >= 40 ? 'text-amber-500' : 'text-red-500'}`} />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-1">{pct}%</h2>
            <p className="text-gray-500">You scored {score} out of {total}</p>
            {results.time_taken_seconds && <p className="text-xs text-gray-400 mt-1">Time: {formatTime(results.time_taken_seconds)}</p>}
            <div className="flex justify-center gap-3 mt-6">
              <button onClick={() => { setPhase('setup'); setResults(null); }}
                className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 text-white rounded-xl text-sm font-medium">
                <RotateCcw className="w-4 h-4" /> New Quiz
              </button>
            </div>
          </div>

          <h3 className="font-semibold text-gray-900 mb-4">Review Answers</h3>
          <div className="space-y-3">
            {answersData.map((a: any, i: number) => (
              <div key={i} className={`bg-white rounded-xl border p-5 ${a.is_correct ? 'border-emerald-200' : 'border-red-200'}`}>
                <div className="text-sm font-medium text-gray-900 mb-2">
                  <MarkdownRenderer content={`${i + 1}. ${a.question || ''}`} />
                </div>
                <div className="flex flex-wrap gap-2 text-xs mb-2">
                  <span className={`px-2 py-1 rounded-full ${a.is_correct ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
                    {a.is_correct ? '✓ Correct' : '✗ Wrong'}
                  </span>
                  {!a.is_correct && <span className="px-2 py-1 rounded-full bg-gray-100 text-gray-600">Your answer: {a.user_answer || 'None'}</span>}
                  <span className="px-2 py-1 rounded-full bg-emerald-50 text-emerald-600">Correct: {a.correct_answer}</span>
                </div>
                {a.explanation && (
                  <div className="text-xs text-gray-500 mt-1">
                    <MarkdownRenderer content={`💡 ${a.explanation}`} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  // Setup Phase
  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8 text-center">
          <div className="w-14 h-14 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <ClipboardCheck className="w-7 h-7 text-purple-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Quiz & Practice</h1>
          <p className="text-gray-500 text-sm mt-1">Test your knowledge with AI-generated quizzes</p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 p-8 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Collection</label>
            <select value={selectedCol} onChange={(e) => setSelectedCol(Number(e.target.value))}
              className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
              <option value={0}>Select Collection</option>
              {collections.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Number of Questions: {questionCount}</label>
            <input type="range" min={5} max={30} value={questionCount} onChange={(e) => setQuestionCount(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600" />
            <div className="flex justify-between text-xs text-gray-400 mt-1"><span>5</span><span>30</span></div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Difficulty</label>
            <div className="flex gap-2">
              {['easy', 'medium', 'hard'].map((d) => (
                <button key={d} onClick={() => setDifficulty(d)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-medium border transition-colors ${
                    difficulty === d ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-200 hover:border-purple-200'
                  }`}>
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Question Type</label>
            <div className="flex gap-2">
              {[{ v: 'mcq', l: 'MCQ' }, { v: 'true_false', l: 'True/False' }, { v: 'mixed', l: 'Mixed' }].map((t) => (
                <button key={t.v} onClick={() => setQType(t.v)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-medium border transition-colors ${
                    qType === t.v ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-200 hover:border-purple-200'
                  }`}>
                  {t.l}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={timerEnabled} onChange={(e) => setTimerEnabled(e.target.checked)}
                className="w-4 h-4 text-purple-600 rounded border-gray-300" />
              <span className="text-sm text-gray-700">Enable Timer</span>
            </label>
            {timerEnabled && (
              <div className="flex items-center gap-2">
                <input type="number" value={timeLimit} onChange={(e) => setTimeLimit(Number(e.target.value))} min={5} max={120}
                  className="w-20 px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-center" />
                <span className="text-sm text-gray-500">minutes</span>
              </div>
            )}
          </div>

          <button onClick={startQuiz} disabled={!selectedCol || generating}
            className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold rounded-xl disabled:opacity-50 shadow-lg shadow-purple-200 text-sm">
            {generating ? <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Generating Quiz...</span> : 'Start Quiz'}
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
