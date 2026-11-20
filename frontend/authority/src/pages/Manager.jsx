import React from 'react';
import Nav from '../components/Nav';
import { useAuth } from '../contexts/AuthContext';

const STAT_CARDS = [
  { label: 'Cities Monitored', value: '4', icon: '🏙️', color: 'bg-cyan-50 border-cyan-200' },
  { label: 'Zones Under Surveillance', value: '16', icon: '📍', color: 'bg-blue-50 border-blue-200' },
  { label: 'Assets Online', value: '108', icon: '⚙️', color: 'bg-emerald-50 border-emerald-200' },
  { label: 'Active Sensors', value: '328', icon: '📡', color: 'bg-amber-50 border-amber-200' },
];

const UPCOMING = [
  { module: 'Network Anomaly Detection', eta: 'M4 Sprint 1' },
  { module: 'Predictive Maintenance AI', eta: 'M4 Sprint 2' },
  { module: 'Cross-City Water Flow Analytics', eta: 'M4 Sprint 2' },
  { module: 'Executive KPI Dashboard', eta: 'M4 Sprint 3' },
  { module: 'Automated Regulatory Reporting', eta: 'M4 Sprint 4' },
];

export default function Manager() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-100">
      <Nav />

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        {/* Welcome banner */}
        <div className="mb-8 overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-cyan-950 p-8 shadow-xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">
                Utility Manager Portal
              </p>
              <h1 className="mt-1 text-2xl font-bold text-white sm:text-3xl">
                Welcome back, {user?.name || 'Manager'} 👋
              </h1>
              <p className="mt-2 max-w-xl text-sm text-slate-400">
                You have full visibility across the municipal water authority
                network. Analytics and reporting features are being built for
                the M4 milestone.
              </p>
            </div>
            <div className="mt-4 shrink-0 sm:mt-0">
              <span className="inline-block rounded-full border border-cyan-500/40 bg-cyan-500/10 px-4 py-1.5 text-xs font-semibold text-cyan-300">
                M4 Analytics — Coming Soon
              </span>
            </div>
          </div>
        </div>

        {/* Stat cards */}
        <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {STAT_CARDS.map((card) => (
            <div
              key={card.label}
              className={`rounded-xl border bg-white p-5 shadow-sm ${card.color}`}
            >
              <div className="mb-2 text-2xl">{card.icon}</div>
              <div className="text-2xl font-bold text-slate-900">{card.value}</div>
              <div className="mt-0.5 text-xs font-medium text-slate-500">
                {card.label}
              </div>
            </div>
          ))}
        </div>

        {/* Coming soon roadmap */}
        <div className="rounded-xl bg-white p-6 shadow-lg">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">
            M4 Analytics Roadmap
          </h2>
          <ul className="divide-y divide-slate-100">
            {UPCOMING.map((item) => (
              <li
                key={item.module}
                className="flex items-center justify-between py-3"
              >
                <div className="flex items-center gap-3">
                  <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
                  <span className="text-sm font-medium text-slate-800">
                    {item.module}
                  </span>
                </div>
                <span className="text-xs font-semibold text-slate-400">
                  {item.eta}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-5 rounded-lg border border-slate-100 bg-slate-50 p-4 text-xs text-slate-500">
            All backend endpoints are live and production-ready. The M4 frontend
            sprint will surface real-time analytics, trend charts, and automated
            SLA reporting directly in this dashboard.
          </p>
        </div>
      </main>
    </div>
  );
}
