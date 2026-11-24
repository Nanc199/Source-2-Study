'use client';
import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { auth } from '@/lib/api';
import { Brain, Eye, EyeOff, Check, X, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Password policy criteria
  const hasMinLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\/~`]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirm;
  const isPasswordValid = hasMinLength && hasUppercase && hasLowercase && hasNumber && hasSpecial;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError('Missing password reset token. Please request a new reset link.');
      return;
    }
    if (!isPasswordValid) {
      setError('Please satisfy all password security requirements.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      await auth.resetPassword({ token, new_password: password });
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Failed to reset password. Link may have expired.');
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
          {success ? (
            <div className="text-center py-4">
              <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Password Reset Complete!</h2>
              <p className="text-gray-600 text-sm mb-6 leading-relaxed">
                Your password has been successfully updated. You can now sign in using your new password.
              </p>
              <Link
                href="/login"
                className="w-full inline-flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-semibold hover:from-purple-700 hover:to-indigo-700 shadow-md shadow-purple-200 transition-all"
              >
                Sign In Now <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          ) : !token ? (
            <div className="text-center py-4">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Invalid Reset Link</h2>
              <p className="text-gray-500 text-sm mb-6">
                This reset link is missing a valid security token. Please request a new password reset link.
              </p>
              <Link
                href="/forgot-password"
                className="inline-flex items-center justify-center py-2.5 px-4 bg-purple-600 text-white rounded-xl text-sm font-semibold hover:bg-purple-700 transition-colors"
              >
                Request Reset Link
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-bold text-gray-900 mb-1">Set New Password</h2>
              <p className="text-gray-500 text-sm mb-6">
                Please enter and confirm your new secure password.
              </p>

              {error && (
                <div className="bg-red-50 border border-red-100 text-red-600 text-sm p-3 rounded-xl mb-4">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPass ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder="Enter new password"
                      className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm pr-11"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass(!showPass)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Password Policy Criteria Checklist */}
                {password && (
                  <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl space-y-1 text-xs">
                    <p className="font-semibold text-gray-600 mb-1">Password must include:</p>
                    <div className="grid grid-cols-2 gap-1 text-[11px]">
                      <div className={`flex items-center gap-1.5 ${hasMinLength ? 'text-emerald-600' : 'text-gray-400'}`}>
                        {hasMinLength ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <X className="w-3.5 h-3.5 text-gray-300" />}
                        <span>8+ characters</span>
                      </div>
                      <div className={`flex items-center gap-1.5 ${hasUppercase ? 'text-emerald-600' : 'text-gray-400'}`}>
                        {hasUppercase ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <X className="w-3.5 h-3.5 text-gray-300" />}
                        <span>1 uppercase letter</span>
                      </div>
                      <div className={`flex items-center gap-1.5 ${hasLowercase ? 'text-emerald-600' : 'text-gray-400'}`}>
                        {hasLowercase ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <X className="w-3.5 h-3.5 text-gray-300" />}
                        <span>1 lowercase letter</span>
                      </div>
                      <div className={`flex items-center gap-1.5 ${hasNumber ? 'text-emerald-600' : 'text-gray-400'}`}>
                        {hasNumber ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <X className="w-3.5 h-3.5 text-gray-300" />}
                        <span>1 number (0-9)</span>
                      </div>
                      <div className={`flex items-center gap-1.5 col-span-2 ${hasSpecial ? 'text-emerald-600' : 'text-gray-400'}`}>
                        {hasSpecial ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <X className="w-3.5 h-3.5 text-gray-300" />}
                        <span>1 special character (@, #, $, %, !, etc.)</span>
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirm ? 'text' : 'password'}
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      required
                      placeholder="Repeat new password"
                      className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm pr-11"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {confirm && (
                    <p className={`text-xs mt-1 ${passwordsMatch ? 'text-emerald-600' : 'text-red-500'}`}>
                      {passwordsMatch ? '✓ Passwords match' : '✗ Passwords do not match'}
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={loading || !isPasswordValid || !passwordsMatch}
                  className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-purple-700 hover:to-indigo-700 transition-all disabled:opacity-50 text-sm shadow-md shadow-purple-200 mt-2"
                >
                  {loading ? 'Updating Password...' : 'Reset Password'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
}
