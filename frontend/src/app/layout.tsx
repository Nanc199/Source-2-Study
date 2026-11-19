import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { Toaster } from 'react-hot-toast';

export const metadata: Metadata = {
  title: 'StudyMind AI - AI-Powered Learning & Exam Preparation',
  description:
    'Transform your study materials into summaries, quizzes, flashcards, and smart question banks with AI-powered learning.',
  keywords: ['AI', 'study', 'learning', 'exam preparation', 'quiz', 'flashcards', 'question bank'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="font-sans antialiased bg-white text-navy-900">
        <AuthProvider>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#0F172A',
                color: '#F8FAFC',
                borderRadius: '12px',
                fontSize: '14px',
                padding: '12px 16px',
              },
              success: {
                iconTheme: { primary: '#7C3AED', secondary: '#F8FAFC' },
              },
              error: {
                iconTheme: { primary: '#EF4444', secondary: '#F8FAFC' },
              },
            }}
          />
        </AuthProvider>
      </body>
    </html>
  );
}
