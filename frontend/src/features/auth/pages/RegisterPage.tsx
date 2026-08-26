import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { AuthLayout } from '../components/AuthLayout';
import { useAuth } from '../../../auth/AuthContext';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!fullName.trim()) return setError('Full name is required.');
    if (!email || !email.includes('@')) return setError('Please enter a valid email address.');
    if (password.length < 6) return setError('Password must be at least 6 characters.');
    if (password !== confirmPassword) return setError('Passwords do not match.');
    if (!agreeTerms) return setError('You must agree to the Terms of Service.');

    try {
      setIsLoading(true);
      await register({ email, password, fullName });
      navigate('/documents', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Failed to create account. Email may already be in use.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="mb-10">
        <h2 className="text-3xl font-medium tracking-tight mb-4">CREATE ACCOUNT</h2>
        <hr className="border-t border-penny-border mb-6 w-12" />
        <p className="text-sm text-[#666666]">Start your workspace.</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6" noValidate>
        {/* Full Name */}
        <div className="flex flex-col gap-2">
          <label htmlFor="fullName" className="text-[10px] uppercase tracking-widest font-semibold">
            Full Name
          </label>
          <input
            id="fullName"
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            disabled={isLoading}
            className="border border-penny-border bg-transparent px-4 py-3 text-sm focus:outline-none focus:border-penny-text transition-colors disabled:opacity-50 rounded-none"
            placeholder="Enter your full name"
          />
        </div>

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
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              className="w-full border border-penny-border bg-transparent px-4 py-3 text-sm focus:outline-none focus:border-penny-text transition-colors disabled:opacity-50 pr-12 rounded-none"
              placeholder="Create a password"
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

        {/* Confirm Password */}
        <div className="flex flex-col gap-2">
          <label htmlFor="confirmPassword" className="text-[10px] uppercase tracking-widest font-semibold">
            Confirm Password
          </label>
          <div className="relative flex items-center">
            <input
              id="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isLoading}
              className="w-full border border-penny-border bg-transparent px-4 py-3 text-sm focus:outline-none focus:border-penny-text transition-colors disabled:opacity-50 pr-12 rounded-none"
              placeholder="Confirm your password"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-4 text-[#666666] hover:text-penny-text transition-colors"
              aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
            >
              {showConfirmPassword ? <EyeOff size={16} strokeWidth={1.5} /> : <Eye size={16} strokeWidth={1.5} />}
            </button>
          </div>
        </div>

        {/* Terms */}
        <div className="flex items-start gap-3 mt-2">
          <input
            type="checkbox"
            id="terms"
            checked={agreeTerms}
            onChange={(e) => setAgreeTerms(e.target.checked)}
            className="mt-1 border-penny-border rounded-none"
          />
          <label htmlFor="terms" className="text-xs text-[#666666] leading-tight">
            I agree to the <span className="text-penny-accent">Terms of Service</span> and <span className="text-penny-accent">Privacy Policy</span>.
          </label>
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
          {isLoading ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT'}
        </button>
      </form>

      <div className="mt-10 pt-6 border-t border-penny-border text-xs flex items-center gap-2">
        <span className="text-[#666666]">Already have an account?</span>
        <Link to="/login" className="text-penny-accent font-medium hover:opacity-80 transition-opacity uppercase tracking-widest">
          SIGN IN →
        </Link>
      </div>
    </AuthLayout>
  );
}