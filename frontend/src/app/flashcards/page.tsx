'use client';
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, flashcardsApi, studyApi } from '@/lib/api';
import { Layers, Heart, ChevronLeft, ChevronRight, Loader2, RotateCcw, Plus, Sparkles } from 'lucide-react';

export default function FlashcardsPage() {
  const searchParams = useSearchParams();
  const presetCol = searchParams.get('collection');
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [cards, setCards] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [showFavOnly, setShowFavOnly] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    collectionsApi.list().then((c: any[]) => {
      setCollections(c);
      if (presetCol) setSelectedCol(Number(presetCol));
      else if (c.length) setSelectedCol(c[0].id);
    });
  }, [presetCol]);

  useEffect(() => {
    if (!selectedCol) return;
    setLoading(true);
    flashcardsApi.list(selectedCol, showFavOnly).then((c: any[]) => {
      setCards(c);
      setCurrentIdx(0);
      setFlipped(false);
    }).finally(() => setLoading(false));
  }, [selectedCol, showFavOnly]);

  const toggleFav = async (id: number) => {
    await flashcardsApi.toggleFavorite(id);
    setCards((prev) => prev.map((c: any) => c.id === id ? { ...c, is_favorite: !c.is_favorite } : c));
  };

  const generateCards = async () => {
    if (!selectedCol) return;
    setGenerating(true);
    try {
      await studyApi.generate(selectedCol, 'flashcards');
      flashcardsApi.list(selectedCol).then(setCards);
    } catch (e: any) { alert(e.message); }
    finally { setGenerating(false); }
  };

  const prev = () => { setCurrentIdx((i) => Math.max(0, i - 1)); setFlipped(false); };
  const next = () => { setCurrentIdx((i) => Math.min(cards.length - 1, i + 1)); setFlipped(false); };

  const currentCard = cards[currentIdx];

  return (
    <DashboardLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Flashcards</h1>
        <p className="text-gray-500 text-sm mt-1">Quick revision with interactive flip cards</p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select value={selectedCol} onChange={(e) => setSelectedCol(Number(e.target.value))}
          className="px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 min-w-[200px]">
          <option value={0}>Select Collection</option>
          {collections.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-600">
          <input type="checkbox" checked={showFavOnly} onChange={(e) => setShowFavOnly(e.target.checked)}
            className="w-4 h-4 text-purple-600 rounded border-gray-300" />
          Favorites only
        </label>
        <button onClick={generateCards} disabled={!selectedCol || generating}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-medium disabled:opacity-50 ml-auto">
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Generate New Cards
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full border-4 border-gray-200 border-t-purple-600 h-10 w-10" /></div>
      ) : cards.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-16 text-center">
          <Layers className="w-16 h-16 mx-auto text-gray-200 mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No flashcards yet</h3>
          <p className="text-gray-400 text-sm mb-6">Generate flashcards from your study materials</p>
          <button onClick={generateCards} disabled={!selectedCol || generating}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-purple-600 text-white rounded-xl text-sm font-medium disabled:opacity-50">
            <Sparkles className="w-4 h-4" /> Generate Flashcards
          </button>
        </div>
      ) : (
        <div className="max-w-2xl mx-auto">
          {/* Card Counter */}
          <div className="text-center mb-4">
            <span className="text-sm text-gray-500">Card {currentIdx + 1} of {cards.length}</span>
            <div className="w-full h-1 bg-gray-100 rounded-full mt-2">
              <div className="h-1 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full transition-all" style={{ width: `${((currentIdx + 1) / cards.length) * 100}%` }} />
            </div>
          </div>

          {/* Flashcard */}
          <div className="perspective-1000 mb-6" style={{ perspective: '1000px' }}>
            <div
              onClick={() => setFlipped(!flipped)}
              className="relative w-full cursor-pointer transition-transform duration-500"
              style={{ transformStyle: 'preserve-3d', transform: flipped ? 'rotateY(180deg)' : '' }}
            >
              {/* Front */}
              <div className="bg-white rounded-3xl border border-gray-100 shadow-lg p-12 min-h-[300px] flex flex-col items-center justify-center"
                style={{ backfaceVisibility: 'hidden' }}>
                <div className="text-xs font-bold text-purple-600 bg-purple-50 px-3 py-1 rounded-full mb-6">QUESTION</div>
                <p className="text-xl font-medium text-gray-900 text-center leading-relaxed">{currentCard?.question}</p>
                <p className="text-xs text-gray-400 mt-8">Click to flip</p>
              </div>

              {/* Back */}
              <div className="bg-gradient-to-br from-purple-600 to-indigo-600 rounded-3xl shadow-lg p-12 min-h-[300px] flex flex-col items-center justify-center absolute inset-0"
                style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}>
                <div className="text-xs font-bold text-purple-200 bg-white/20 px-3 py-1 rounded-full mb-6">ANSWER</div>
                <p className="text-xl font-medium text-white text-center leading-relaxed">{currentCard?.answer}</p>
                <p className="text-xs text-purple-200 mt-8">Click to flip back</p>
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between">
            <button onClick={prev} disabled={currentIdx === 0}
              className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>

            <button onClick={() => currentCard && toggleFav(currentCard.id)}
              className={`p-3 rounded-xl transition-colors ${currentCard?.is_favorite ? 'bg-red-50 text-red-500' : 'bg-gray-50 text-gray-400 hover:text-red-400'}`}>
              <Heart className={`w-5 h-5 ${currentCard?.is_favorite ? 'fill-current' : ''}`} />
            </button>

            <button onClick={next} disabled={currentIdx >= cards.length - 1}
              className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-xl text-sm font-medium hover:bg-purple-700 disabled:opacity-50">
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Card Grid */}
          <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 gap-3">
            {cards.map((c: any, i: number) => (
              <button key={c.id} onClick={() => { setCurrentIdx(i); setFlipped(false); }}
                className={`p-3 rounded-xl text-left text-xs border transition-colors ${
                  i === currentIdx ? 'border-purple-500 bg-purple-50' : 'border-gray-100 bg-white hover:bg-gray-50'
                }`}>
                <p className="font-medium text-gray-700 line-clamp-2">{c.question}</p>
                {c.is_favorite && <Heart className="w-3 h-3 text-red-400 fill-current mt-1" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
