'use client';
import React from 'react';
import Link from 'next/link';
import {
  Upload, MessageSquare, BookOpen, GitCompareArrows, ClipboardCheck,
  Layers, ArrowRight, Brain, Sparkles, FileText, Globe, Youtube,
  Image, CheckCircle2, ChevronRight, Star, Zap
} from 'lucide-react';

const features = [
  { icon: Upload, title: 'Multi-Source Upload', desc: 'Upload PDFs, DOCX, PPTX, images, URLs, and YouTube videos all in one place.', color: 'from-blue-500 to-cyan-500' },
  { icon: MessageSquare, title: 'AI Chat Assistant', desc: 'Ask questions about your study materials and get accurate, sourced answers.', color: 'from-purple-500 to-pink-500' },
  { icon: BookOpen, title: 'Smart Study Generator', desc: 'Auto-generate summaries, MCQs, flashcards, and exam-oriented answers.', color: 'from-amber-500 to-orange-500' },
  { icon: GitCompareArrows, title: 'Duplicate Detection', desc: 'Combine question papers and detect semantically similar questions using AI.', color: 'from-emerald-500 to-teal-500' },
  { icon: ClipboardCheck, title: 'Interactive Quizzes', desc: 'Take timed quizzes with instant scoring and detailed explanations.', color: 'from-red-500 to-rose-500' },
  { icon: Layers, title: 'Flashcards & Notes', desc: 'Flip-card flashcards and chapter-wise notes for quick revision.', color: 'from-indigo-500 to-violet-500' },
];

const steps = [
  { num: '01', title: 'Upload Your Materials', desc: 'Drag and drop PDFs, docs, presentations, images, or paste URLs.' },
  { num: '02', title: 'AI Processes Everything', desc: 'Our AI extracts, understands, and indexes all your content.' },
  { num: '03', title: 'Study Smarter', desc: 'Get summaries, quizzes, flashcards, and a smart question bank.' },
];

const sourceTypes = [
  { icon: FileText, label: 'PDF', color: 'bg-red-50 text-red-600' },
  { icon: FileText, label: 'DOCX', color: 'bg-blue-50 text-blue-600' },
  { icon: FileText, label: 'PPTX', color: 'bg-orange-50 text-orange-600' },
  { icon: Image, label: 'Images', color: 'bg-green-50 text-green-600' },
  { icon: Globe, label: 'Websites', color: 'bg-purple-50 text-purple-600' },
  { icon: Youtube, label: 'YouTube', color: 'bg-rose-50 text-rose-600' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="fixed top-0 w-full bg-white/80 backdrop-blur-xl border-b border-gray-100 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-gray-900">Source2Study</span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Features</a>
            <a href="#how-it-works" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">How It Works</a>
            <a href="#duplicate" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">Duplicate Detection</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm font-medium text-gray-700 hover:text-gray-900 px-4 py-2">Sign In</Link>
            <Link href="/signup" className="text-sm font-medium text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 px-5 py-2.5 rounded-xl shadow-lg shadow-purple-200 transition-all">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-purple-50/50 via-white to-white" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-purple-100 rounded-full blur-3xl opacity-30" />
        <div className="absolute top-40 right-1/4 w-96 h-96 bg-indigo-100 rounded-full blur-3xl opacity-30" />

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 bg-purple-50 border border-purple-100 rounded-full px-4 py-1.5 mb-8">
            <Sparkles className="w-4 h-4 text-purple-600" />
            <span className="text-sm font-medium text-purple-700">Powered by Google Gemini AI</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold text-gray-900 leading-[1.1] mb-6 tracking-tight">
            Upload Anything.
            <br />
            <span className="bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Learn Everything.
            </span>
            <br />
            Prepare Smarter.
          </h1>

          <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed">
            AI-powered learning platform that transforms your study materials into summaries, quizzes, flashcards, and a smart duplicate-free question bank.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Link href="/signup" className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold px-8 py-4 rounded-2xl shadow-xl shadow-purple-200 hover:shadow-2xl hover:shadow-purple-300 transition-all text-lg">
              Get Started <ArrowRight className="w-5 h-5" />
            </Link>
            <a href="#features" className="inline-flex items-center justify-center gap-2 bg-white text-gray-700 font-semibold px-8 py-4 rounded-2xl border border-gray-200 hover:border-gray-300 hover:shadow-lg transition-all text-lg">
              See Features
            </a>
          </div>

          {/* Source types */}
          <div className="flex flex-wrap justify-center gap-3 mb-12">
            {sourceTypes.map((s) => (
              <div key={s.label} className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl ${s.color} text-sm font-medium`}>
                <s.icon className="w-4 h-4" /> {s.label}
              </div>
            ))}
          </div>

          {/* Mini Dashboard Preview */}
          <div className="max-w-4xl mx-auto bg-white rounded-3xl shadow-2xl shadow-gray-200/60 border border-gray-100 overflow-hidden">
            <div className="bg-gray-50 border-b border-gray-100 px-6 py-3 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <div className="w-3 h-3 rounded-full bg-yellow-400" />
              <div className="w-3 h-3 rounded-full bg-green-400" />
              <span className="ml-4 text-xs text-gray-400 font-mono">source2study.ai/dashboard</span>
            </div>
            <div className="p-8 grid grid-cols-4 gap-4">
              {[
                { label: 'Sources', value: '24', color: 'text-blue-600 bg-blue-50' },
                { label: 'Collections', value: '5', color: 'text-purple-600 bg-purple-50' },
                { label: 'Questions', value: '250', color: 'text-emerald-600 bg-emerald-50' },
                { label: 'Quizzes', value: '12', color: 'text-amber-600 bg-amber-50' },
              ].map((s) => (
                <div key={s.label} className={`${s.color} rounded-2xl p-4 text-center`}>
                  <div className="text-2xl font-bold">{s.value}</div>
                  <div className="text-xs font-medium mt-1 opacity-80">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 bg-gray-50/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Everything You Need to Study Smarter</h2>
            <p className="text-gray-500 text-lg max-w-2xl mx-auto">Powered by AI, designed for students who want to ace their exams.</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div key={f.title} className="bg-white rounded-2xl p-7 border border-gray-100 hover:shadow-xl hover:shadow-gray-100 transition-all duration-300 group relative">
                <div className={`w-12 h-12 bg-gradient-to-br ${f.color} rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
                  <f.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">How It Works</h2>
            <p className="text-gray-500 text-lg">Three simple steps to transform your study experience.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((s, i) => (
              <div key={s.num} className="text-center relative">
                <div className="text-6xl font-extrabold text-purple-100 mb-4">{s.num}</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
                {i < 2 && <ChevronRight className="hidden md:block absolute top-12 -right-4 w-8 h-8 text-gray-200" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Duplicate Detection Showcase */}
      <section id="duplicate" className="py-24 px-6 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-100 rounded-full px-4 py-1.5 mb-4">
              <Star className="w-4 h-4 text-emerald-600" />
              <span className="text-sm font-medium text-emerald-700">Exam Paper Analysis</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Smart Duplicate Question Detection</h2>
            <p className="text-gray-500 text-lg max-w-2xl mx-auto">Upload multiple question papers and get one consolidated document with zero repeated questions.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Upload className="w-5 h-5 text-purple-600" /> Upload Papers
              </h4>
              <div className="space-y-2">
                {['Paper 2021.pdf', 'Paper 2022.pdf', 'Paper 2023.pdf', 'Paper 2024.pdf', 'Paper 2025.pdf'].map((p) => (
                  <div key={p} className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                    <FileText className="w-4 h-4 text-red-400" /> {p}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center mb-4">
                <Zap className="w-8 h-8 text-white" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">AI Analysis</h4>
              <p className="text-sm text-gray-500 text-center">Semantic comparison using embeddings + LLM verification</p>
            </div>

            <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" /> Results
              </h4>
              <div className="space-y-3">
                <div className="flex justify-between text-sm"><span className="text-gray-600">Total Questions</span><span className="font-bold text-gray-900">250</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">Unique Questions</span><span className="font-bold text-emerald-600">165</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">Duplicates Found</span><span className="font-bold text-red-500">85</span></div>
                <div className="w-full bg-gray-100 rounded-full h-2 mt-2">
                  <div className="bg-gradient-to-r from-emerald-500 to-teal-500 h-2 rounded-full" style={{ width: '66%' }} />
                </div>
                <p className="text-xs text-gray-400 text-center">34% duplicate questions removed</p>
              </div>
            </div>
          </div>

          {/* Example */}
          <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm max-w-3xl mx-auto">
            <h4 className="font-semibold text-gray-900 mb-4">Example: These are detected as the SAME question</h4>
            <div className="space-y-2 mb-4">
              {[
                { year: '2021', q: 'What is Artificial Intelligence? Explain its applications.' },
                { year: '2022', q: 'Define AI and discuss its major applications.' },
                { year: '2023', q: 'Explain Artificial Intelligence and mention its real-world applications.' },
              ].map((e) => (
                <div key={e.year} className="flex items-start gap-3 bg-purple-50 rounded-xl px-4 py-3">
                  <span className="text-xs font-bold text-purple-600 bg-purple-100 rounded px-2 py-0.5 mt-0.5">{e.year}</span>
                  <span className="text-sm text-gray-700">{e.q}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 text-sm text-emerald-600 font-medium">
              <CheckCircle2 className="w-4 h-4" />
              Consolidated into 1 unique question — appeared 3 times
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Ready to Transform Your Study Experience?</h2>
          <p className="text-gray-500 text-lg mb-10">Join thousands of students preparing smarter with AI-powered tools.</p>
          <Link href="/signup" className="inline-flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold px-8 py-4 rounded-2xl shadow-xl shadow-purple-200 hover:shadow-2xl transition-all text-lg">
            Get Started <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-50 border-t border-gray-100 py-12 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-gray-900">Source2Study</span>
          </div>
          <p className="text-sm text-gray-400">© 2024 Source2Study. Built for students, powered by AI.</p>
        </div>
      </footer>
    </div>
  );
}
