import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { Activity, Lock, Mail, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate   = useNavigate();

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(role: 'Doctor' | 'Patient') {
    if (role === 'Doctor') {
      setEmail('doctor@cardioguard.ai');
      setPassword('doctor123');
    } else {
      setEmail('patient@cardioguard.ai');
      setPassword('patient123');
    }
  }

  return (
    <div className="min-h-screen bg-cg-bg flex items-center justify-center p-4">
      {/* Background decorative blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mb-4 glow-indigo">
            <Activity className="w-8 h-8 text-indigo-400" />
          </div>
          <h1 className="text-3xl font-bold text-gradient-primary">CardioGuard AI</h1>
          <p className="text-cg-muted text-sm mt-1">Clinical Decision Support System</p>
        </div>

        {/* Card */}
        <div className="glass-card p-8">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in to your account</h2>

          {error && (
            <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20
                            rounded-xl px-4 py-3 mb-5 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-cg-muted mb-1.5 uppercase tracking-wide">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cg-muted" />
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="you@cardioguard.ai"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-cg-muted mb-1.5 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cg-muted" />
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-10"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              id="btn-login"
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-3 mt-2"
            >
              {loading ? (
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              ) : null}
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          {/* Demo shortcuts */}
          <div className="mt-6 pt-6 border-t border-white/5">
            <p className="text-xs text-cg-muted text-center mb-3">Demo quick-fill</p>
            <div className="flex gap-3">
              <button
                id="btn-demo-doctor"
                type="button"
                onClick={() => fillDemo('Doctor')}
                className="btn-ghost flex-1 justify-center text-xs"
              >
                👨‍⚕️ Doctor Demo
              </button>
              <button
                id="btn-demo-patient"
                type="button"
                onClick={() => fillDemo('Patient')}
                className="btn-ghost flex-1 justify-center text-xs"
              >
                🏥 Patient Demo
              </button>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-cg-muted mt-6">
          © {new Date().getFullYear()} CardioGuard AI · All clinical data is encrypted in transit
        </p>
      </div>
    </div>
  );
}
