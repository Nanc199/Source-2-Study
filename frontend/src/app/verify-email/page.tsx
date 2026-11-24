'use client';
import React, { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { auth } from '@/lib/api';
import { Brain, CheckCircle2, XCircle, Loader2, ArrowRight, RefreshCw, Mail } from 'lucide-react';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [message, setMessage] = useState('');
  const [resendEmail, setResendEmail] = useState('');
  const [resending, setResending] = useState(false);
  const [resendStatus, setResendStatus] = useState('');

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setSuccess(false);
      setMessage('No verification token was provided in the link.');
      return;
    }

    auth.verifyEmail(token)
      .then((res: any) => {
        setSuccess(true);
        setMessage(res.message || 'Email verified successfully! You may now sign in.');
      })
      .catch((err: any) => {
        setSuccess(false);
        setMessage(err.message || 'Verification token is invalid or has expired.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resendEmail.trim()) return;
    setResending(true);
    setResendStatus('');
    try {
      const res = await auth.resendVerification(resendEmail.trim());
      setResendStatus(res.message || 'Verification link sent. Please check your inbox.');
    } catch (err: any) {
      setResendStatus(err.message || 'Could not send verification email.');
    } finally {
      setResending(false);
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
        <div className="bg-white py-8 px-6 shadow-sm border border-gray-100 rounded-2xl sm:px-10 text-center">
          {loading ? (
            <div className="py-10">
              <Loader2 className="w-10 h-10 text-purple-600 animate-spin mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-gray-900 mb-1">Verifying Email Address</h2>
              <p className="text-gray-500 text-xs">Please wait a moment while we activate your account...</p>
            </div>
          ) : success ? (
            <div className="py-4">
              <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Account Verified!</h2>
              <p className="text-gray-600 text-sm mb-6 leading-relaxed">
                {message}
              </p>
              <Link
                href="/login"
                className="w-full inline-flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-semibold hover:from-purple-700 hover:to-indigo-700 shadow-md shadow-purple-200 transition-all"
              >
                Sign In to Your Account <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          ) : (
            <div className="py-4">
              <div className="w-14 h-14 bg-red-50 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <XCircle className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Verification Failed</h2>
              <p className="text-gray-600 text-sm mb-6 leading-relaxed">
                {message}
              </p>

              <div className="border-t border-gray-100 pt-6 text-left">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-700 mb-2">
                  Request a New Verification Link
                </h3>
                <form onSubmit={handleResend} className="space-y-3">
                  <div className="relative">
                    <Mail className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      value={resendEmail}
                      onChange={(e) => setResendEmail(e.target.value)}
                      placeholder="Enter registered email"
                      required
                      className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={resending || !resendEmail}
                    className="w-full inline-flex items-center justify-center gap-2 py-2 px-4 bg-purple-600 text-white rounded-xl text-xs font-semibold hover:bg-purple-700 transition-all disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${resending ? 'animate-spin' : ''}`} />
                    {resending ? 'Sending...' : 'Send New Link'}
                  </button>
                </form>
                {resendStatus && (
                  <p className="text-xs text-purple-700 mt-2 bg-purple-50 p-2 rounded-lg">
                    {resendStatus}
                  </p>
                )}
              </div>

              <div className="mt-6 pt-4 border-t border-gray-100">
                <Link href="/login" className="text-xs font-medium text-purple-600 hover:text-purple-700">
                  Return to Sign In
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
