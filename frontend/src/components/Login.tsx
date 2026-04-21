import React, { useState, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import ThirdEyeLogo from './ThirdEyeLogo';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPrivate, setIsPrivate] = useState(false);

  // Defer blur so tabbing between sensitive fields doesn't flash
  const blurTimeout = useRef<ReturnType<typeof setTimeout>>();
  const handleSensitiveFocus = () => {
    clearTimeout(blurTimeout.current);
    setIsPrivate(true);
  };
  const handleSensitiveBlur = () => {
    blurTimeout.current = setTimeout(() => setIsPrivate(false), 80);
  };

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#FAF9F7' }}>
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <ThirdEyeLogo isPrivate={isPrivate} bgColor="#FAF9F7" width={176} height={130} />
          <h1 className="font-display font-bold text-3xl -mt-2" style={{ color: '#1A1714', letterSpacing: '-0.04em' }}>
            ThirdEye
          </h1>
          <p className="text-sm text-stone-500 mt-1">
            {isPrivate ? 'Not looking, promise.' : 'Sign in to your account'}
          </p>
        </div>

        {/* Card */}
        <div className="bg-white border border-stone-200 rounded-xl p-6" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          {error && (
            <div className="mb-4 px-3 py-2 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-stone-700 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onFocus={handleSensitiveFocus}
                onBlur={handleSensitiveBlur}
                required
                className="input"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-stone-700 mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={handleSensitiveFocus}
                onBlur={handleSensitiveBlur}
                required
                className="input"
                placeholder="Enter your password"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50"
              style={{ background: '#1A1714' }}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-stone-500 mt-4">
          Don't have an account?{' '}
          <Link to="/signup" className="text-stone-700 hover:text-stone-900 font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
