import React, { useEffect, useState } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import { authApi } from '../services/auth';

const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token');
      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link.');
        return;
      }
      try {
        const response = await authApi.verifyEmail(token);
        setStatus('success');
        setMessage(response.message);
        setTimeout(() => navigate('/login'), 3000);
      } catch (error: any) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Failed to verify email.');
      }
    };
    verifyEmail();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#FAF9F7' }}>
      <div className="w-full max-w-sm">
        <div className="bg-white border border-stone-200 rounded-xl shadow-sm p-8 text-center">
          {status === 'loading' && (
            <>
              <div className="inline-block w-8 h-8 border-2 border-stone-700 border-t-transparent rounded-full animate-spin mb-4" />
              <h2 className="text-lg font-semibold text-stone-900 mb-1">Verifying your email</h2>
              <p className="text-sm text-stone-500">Please wait a moment...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="inline-flex items-center justify-center w-10 h-10 bg-green-100 rounded-full mb-4">
                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-stone-900 mb-2">Email verified</h2>
              <p className="text-sm text-stone-500 mb-4">{message}</p>
              <p className="text-xs text-stone-400">Redirecting to login...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="inline-flex items-center justify-center w-10 h-10 bg-red-100 rounded-full mb-4">
                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-stone-900 mb-2">Verification failed</h2>
              <p className="text-sm text-red-600 mb-6">{message}</p>
              <Link to="/login" className="btn-primary inline-block">
                Go to login
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;
