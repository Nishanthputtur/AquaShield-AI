import React, { useCallback, useEffect, useState } from 'react';
import Nav from '../components/Nav';
import { useAuth } from '../contexts/AuthContextStore';
import api from '../services/api';

const ROLES = [
  'Administrator',
  'Engineer',
  'Maintenance Officer',
  'Field Inspector',
  'Utility Manager',
];

const ROLE_BADGE = {
  Administrator: 'bg-purple-100 text-purple-800',
  Engineer: 'bg-blue-100 text-blue-800',
  'Maintenance Officer': 'bg-amber-100 text-amber-800',
  'Field Inspector': 'bg-cyan-100 text-cyan-800',
  'Utility Manager': 'bg-emerald-100 text-emerald-800',
};

export default function Admin() {
  const { token } = useAuth();

  // ── Users list ────────────────────────────────────────────────────────────
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState('');

 const fetchUsers = useCallback(async () => {
  try {
    const data = await api.getUsers(token);
    setUsersError('');
    setUsers(data.users || data || []);
  } catch (err) {
    setUsersError(err.message || 'Failed to load users');
  } finally {
    setUsersLoading(false);
  }
}, [token]);

  useEffect(() => {
  let isMounted = true;

  async function loadUsers() {
    try {
      const data = await api.getUsers(token);

      if (isMounted) {
        setUsers(data.users || data || []);
        setUsersError('');
      }
    } catch (err) {
      if (isMounted) {
        setUsersError(err.message || 'Failed to load users');
      }
    } finally {
      if (isMounted) {
        setUsersLoading(false);
      }
    }
  }

  loadUsers();

  return () => {
    isMounted = false;
  };
}, [token]);
  // ── Create-user form ──────────────────────────────────────────────────────
  const [formName, setFormName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formRole, setFormRole] = useState('Engineer');
  const [formLoading, setFormLoading] = useState(false);
  const [formSuccess, setFormSuccess] = useState('');
  const [formError, setFormError] = useState('');

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormSuccess('');
    setFormError('');

    if (formPassword.length < 8) {
      setFormError('Password must be at least 8 characters.');
      return;
    }

    setFormLoading(true);
    try {
      const res = await api.createUser(token, {
        name: formName.trim(),
        email: formEmail.trim(),
        password: formPassword,
        role: formRole,
      });
      setFormSuccess(
        `User created: ${res.name} (${res.role}) — ID ${res.user_id}`
      );
      setFormName('');
      setFormEmail('');
      setFormPassword('');
      setFormRole('Engineer');
      setUsersLoading(true);
      setUsersError('');
      fetchUsers();
    } catch (err) {
      const detail = err.detail;
      setFormError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : err.message || 'Failed to create user'
      );
    } finally {
      setFormLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Nav />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            User Management
          </h1>
          <p className="text-sm text-slate-500">
            View authority personnel and provision new accounts
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Users table — takes 2 of 3 columns on large screens */}
          <div className="rounded-xl bg-white p-6 shadow-lg lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                Authority Personnel ({users.length})
              </h2>
              <button
                onClick={fetchUsers}
                className="text-xs font-medium text-cyan-600 hover:underline"
              >
                Refresh
              </button>
            </div>

            {usersLoading && (
              <p className="text-sm text-slate-400">Loading users…</p>
            )}
            {usersError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                {usersError}
              </div>
            )}

            {users.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      <th className="pb-2 pr-4">ID</th>
                      <th className="pb-2 pr-4">Name</th>
                      <th className="pb-2 pr-4">Email</th>
                      <th className="pb-2 pr-4">Role</th>
                      <th className="pb-2">Joined</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {users.map((u) => (
                      <tr key={u.user_id} className="hover:bg-slate-50">
                        <td className="py-2 pr-4 font-mono text-xs text-slate-400">
                          {u.user_id}
                        </td>
                        <td className="py-2 pr-4 font-medium text-slate-800">
                          {u.name}
                        </td>
                        <td className="py-2 pr-4 text-slate-600">{u.email}</td>
                        <td className="py-2 pr-4">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                              ROLE_BADGE[u.role] || 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="py-2 text-xs text-slate-400">
                          {u.created_at
                            ? new Date(u.created_at).toLocaleDateString()
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {!usersLoading && users.length === 0 && !usersError && (
              <p className="text-sm text-slate-400">No users found.</p>
            )}
          </div>

          {/* Create-user form — 1 column */}
          <div className="rounded-xl bg-white p-6 shadow-lg">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">
              Create New User
            </h2>

            {formSuccess && (
              <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                {formSuccess}
              </div>
            )}
            {formError && (
              <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Jane Smith"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Email <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  placeholder="jane@aquashield.demo"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Password{' '}
                  <span className="text-slate-400 font-normal">(min 8 chars)</span>{' '}
                  <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={formPassword}
                  onChange={(e) => setFormPassword(e.target.value)}
                  placeholder="••••••••"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Role <span className="text-rose-500">*</span>
                </label>
                <select
                  value={formRole}
                  onChange={(e) => setFormRole(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={formLoading}
                className="w-full rounded-lg bg-cyan-600 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-cyan-700 disabled:opacity-50"
              >
                {formLoading ? 'Creating…' : 'Create User'}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
