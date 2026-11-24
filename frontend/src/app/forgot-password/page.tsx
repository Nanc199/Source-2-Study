'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { auth } from '@/lib/api';
import { Brain, Mail, ArrowLeft, CheckCircle2, ArrowRight } from 'lucide-react';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setError('');
    setLoading(true);
    try {
      await auth.forgotPassword(email.trim());
      setSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 px-6 sm:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-6">
        <Link href="/" className="inline-flex items-center gap-2 mb-2">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <span className="font-bold text-xl text-gray-900">Source2Study</span>
        </Link>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-gray-100 rounded-2xl sm:px-10">
          {submitted ? (
            <div className="text-center py-2">
              <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Check Your Email</h2>
              <p className="text-gray-600 text-sm mb-4 leading-relaxed">
                If an account exists with <strong>{email}</strong>, we have sent password reset instructions to your inbox.
              </p>
              <p className="text-xs text-gray-400 mb-6 leading-relaxed">
                The link in the email is valid for 1 hour. Please check your spam folder if you do not receive it.
              </p>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => setSubmitted(false)}
                  className="w-full py-2.5 px-4 border border-gray-200 text-gray-700 hover:bg-gray-50 rounded-xl text-sm font-medium transition-colors"
                >
                  Try Another Email
                </button>
                <Link
                  href="/login"
                  className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-purple-600 text-white rounded-xl text-sm font-semibold hover:bg-purple-700 transition-colors"
                >
                  Return to Sign In <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-bold text-gray-900 mb-1">Forgot Password?</h2>
              <p className="text-gray-500 text-sm mb-6">
                Enter your registered email address and we'll send you a link to reset your password.
              </p>

              {error && (
                <div className="bg-red-50 border border-red-100 text-red-600 text-sm p-3 rounded-xl mb-4">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="you@example.com"
                      className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-purple-700 hover:to-indigo-700 transition-all disabled:opacity-50 text-sm shadow-md shadow-purple-200"
                >
                  {loading ? 'Sending Instructions...' : 'Send Password Reset Link'}
                </button>
              </form>

              <div className="mt-6 pt-4 border-t border-gray-100 text-center">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-purple-600 hover:text-purple-700"
                >
                  <ArrowLeft className="w-4 h-4" /> Back to Sign In
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
