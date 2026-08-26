import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { AuthLayout } from '../components/AuthLayout';
import { useAuth } from '../../../auth/AuthContext';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !email.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setError('Password is required.');
      return;
    }

    try {
      setIsLoading(true);
      await login({ email, password });
      navigate('/documents', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Invalid credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="mb-10">
        <h2 className="text-3xl font-medium tracking-tight mb-4">SIGN IN</h2>
        <hr className="border-t border-penny-border mb-6 w-12" />
        <p className="text-sm text-[#666666]">Welcome back.</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6" noValidate>
        {/* Email */}
        <div className="flex flex-col gap-2">
          <label htmlFor="email" className="text-[10px] uppercase tracking-widest font-semibold">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            className="border border-penny-border bg-transparent px-4 py-3 text-sm focus:outline-none focus:border-penny-text transition-colors disabled:opacity-50 rounded-none"
            placeholder="you@example.com"
          />
        </div>

        {/* Password */}
        <div className="flex flex-col gap-2">
          <label htmlFor="password" className="text-[10px] uppercase tracking-widest font-semibold">
            Password
          </label>
          <div className="relative flex items-center">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              className="w-full border border-penny-border bg-transparent px-4 py-3 text-sm focus:outline-none focus:border-penny-text transition-colors disabled:opacity-50 pr-12 rounded-none"
              placeholder="••••••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 text-[#666666] hover:text-penny-text transition-colors"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff size={16} strokeWidth={1.5} /> : <Eye size={16} strokeWidth={1.5} />}
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="text-xs text-penny-accent font-medium">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="mt-2 w-full bg-penny-text text-penny-bg py-3.5 text-xs uppercase tracking-widest font-semibold hover:bg-black transition-colors disabled:opacity-70 rounded-none"
        >
          {isLoading ? 'SIGNING IN...' : 'SIGN IN'}
        </button>
      </form>

      <div className="mt-10 pt-6 border-t border-penny-border text-xs flex items-center gap-2">
        <span className="text-[#666666]">Don't have an account?</span>
        <Link to="/register" className="text-penny-accent font-medium hover:opacity-80 transition-opacity uppercase tracking-widest">
          CREATE ACCOUNT →
        </Link>
      </div>
    </AuthLayout>
  );
}