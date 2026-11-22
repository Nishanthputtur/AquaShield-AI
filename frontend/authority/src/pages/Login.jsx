import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { roleHome } from '../utils/roleHome';
import { useAuth } from '../contexts/AuthContextStore';

const DEMO_USERS = [
  { label: 'Admin', email: 'admin@aquashield.demo', role: 'Administrator' },
  { label: 'Engineer', email: 'engineer@aquashield.demo', role: 'Engineer' },
  { label: 'Maintenance', email: 'maintenance@aquashield.demo', role: 'Maintenance Officer' },
  { label: 'Inspector', email: 'inspector@aquashield.demo', role: 'Field Inspector' },
  { label: 'Manager', email: 'manager@aquashield.demo', role: 'Utility Manager' },
];

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      navigate(roleHome(user.role), { replace: true });
    }
  }, [user, navigate]);

  const executeLogin = async (loginEmail, loginPassword) => {
    setErrorMessage('');
    setIsSubmitting(true);
    try {
      const loggedUser = await login(loginEmail, loginPassword);
      navigate(roleHome(loggedUser.role), { replace: true });
    } catch {
      setErrorMessage('Invalid email or password');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    executeLogin(email, password);
  };

  const handleQuickLogin = (demoEmail) => {
    setEmail(demoEmail);
    setPassword('password123');
    executeLogin(demoEmail, 'password123');
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-cyan-950 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6 rounded-2xl bg-white/95 p-8 shadow-2xl backdrop-blur">
        <div className="text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-600 text-2xl font-bold text-white shadow-lg shadow-cyan-600/30">
            AQ
          </div>
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            AquaShield AI
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Sign in to access authority monitoring & workflows
          </p>
        </div>

        {errorMessage && (
          <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 border border-rose-200">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@aquashield.demo"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-cyan-600 py-2.5 text-sm font-semibold text-white shadow-md transition-colors hover:bg-cyan-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 disabled:opacity-60"
          >
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="border-t border-slate-200 pt-5">
          <p className="mb-2 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
            Demo Quick Login
          </p>
          <div className="grid grid-cols-5 gap-1.5">
            {DEMO_USERS.map((demo) => (
              <button
                key={demo.label}
                type="button"
                onClick={() => handleQuickLogin(demo.email)}
                disabled={isSubmitting}
                className="rounded-md border border-slate-200 bg-slate-50 px-1 py-1.5 text-center text-xs font-medium text-slate-700 transition hover:border-cyan-400 hover:bg-cyan-50 hover:text-cyan-800 disabled:opacity-50"
              >
                {demo.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
