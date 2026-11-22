import React, { useCallback, useEffect, useState } from 'react';
import Nav from '../components/Nav';
import { useAuth } from '../contexts/AuthContextStore';
import api from '../services/api';

export default function Maintenance() {
  const { token } = useAuth();

  // ── Inspections (left panel) ──────────────────────────────────────────────
  const [inspections, setInspections] = useState([]);
  const [inspectionsLoading, setInspectionsLoading] = useState(true);
  const [inspectionsError, setInspectionsError] = useState('');

  const fetchInspections = useCallback(async () => {
  try {
    const data = await api.getInspections(token);
    setInspectionsError('');
    setInspections(data.inspections || []);
  } catch (err) {
    setInspectionsError(err.message || 'Failed to load inspections');
  } finally {
    setInspectionsLoading(false);
  }
}, [token]);

  useEffect(() => {
  let isMounted = true;

  async function loadInspections() {
    try {
      const data = await api.getInspections(token);

      if (isMounted) {
        setInspections(data.inspections || []);
        setInspectionsError('');
      }
    } catch (err) {
      if (isMounted) {
        setInspectionsError(err.message || 'Failed to load inspections');
      }
    } finally {
      if (isMounted) {
        setInspectionsLoading(false);
      }
    }
  }

  loadInspections();

  return () => {
    isMounted = false;
  };
}, [token]);
  // ── Maintenance records (bottom table) ───────────────────────────────────
  const [records, setRecords] = useState([]);
  const [recordsLoading, setRecordsLoading] = useState(true);
  const [recordsError, setRecordsError] = useState('');

  const fetchRecords = useCallback(async () => {
  try {
    const data = await api.getMaintenance(token);
    setRecordsError('');
    setRecords(data.maintenance_records || []);
  } catch (err) {
    setRecordsError(err.message || 'Failed to load maintenance records');
  } finally {
    setRecordsLoading(false);
  }
}, [token]);

  useEffect(() => {
  let isMounted = true;

  async function loadRecords() {
    try {
      const data = await api.getMaintenance(token);

      if (isMounted) {
        setRecords(data.maintenance_records || []);
        setRecordsError('');
      }
    } catch (err) {
      if (isMounted) {
        setRecordsError(err.message || 'Failed to load maintenance records');
      }
    } finally {
      if (isMounted) {
        setRecordsLoading(false);
      }
    }
  }

  loadRecords();

  return () => {
    isMounted = false;
  };
}, [token]);;

  // ── Create-maintenance form (right panel) ─────────────────────────────────
  const [formAssetId, setFormAssetId] = useState('');
  const [formDetails, setFormDetails] = useState('');
  const [formStatus, setFormStatus] = useState('Scheduled');
  const [formNotes, setFormNotes] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  const [formSuccess, setFormSuccess] = useState('');
  const [formError, setFormError] = useState('');

  const handleCreateMaintenance = async (e) => {
    e.preventDefault();
    setFormSuccess('');
    setFormError('');
    setFormLoading(true);
    try {
      const payload = {
        asset_id: formAssetId.trim(),
        maintenance_details: formDetails.trim(),
        status: formStatus,
      };
      if (formNotes.trim()) payload.notes = formNotes.trim();
      const res = await api.createMaintenance(token, payload);
      setFormSuccess(`Maintenance record created (ID: ${res.maintenance_id})`);
      setFormAssetId('');
      setFormDetails('');
      setFormStatus('Scheduled');
      setFormNotes('');
      setRecordsLoading(true);
      setRecordsError('');
      fetchRecords();
    } catch (err) {
      const detail = err.detail;
      setFormError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : err.message || 'Failed to create maintenance record'
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
            Maintenance Officer
          </h1>
          <p className="text-sm text-slate-500">
            Review outstanding field inspections and log maintenance actions
          </p>
        </div>

        {/* Top row: inspections (left) + create form (right) */}
        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Inspections panel */}
          <div className="rounded-xl bg-white p-6 shadow-lg">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                Field Inspections
              </h2>
              <button
                onClick={() => {
  setInspectionsLoading(true);
  setInspectionsError('');
  fetchInspections();
}}
                className="text-xs font-medium text-cyan-600 hover:underline"
              >
                Refresh
              </button>
            </div>

            {inspectionsLoading && (
              <p className="text-sm text-slate-400">Loading inspections…</p>
            )}
            {inspectionsError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                {inspectionsError}
              </div>
            )}
            {!inspectionsLoading && inspections.length === 0 && !inspectionsError && (
              <p className="text-sm text-slate-400">No inspections on record.</p>
            )}

            <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto">
              {inspections.map((insp) => (
                <li key={insp.inspection_id} className="py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-sm font-semibold text-slate-800">
                        {insp.asset?.name || insp.asset_id}
                      </span>
                      <p className="mt-0.5 text-xs text-slate-500 line-clamp-2">
                        {insp.findings}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <span className="text-xs font-medium text-slate-500">
                        {insp.condition || '—'}
                      </span>
                      <p className="text-xs text-slate-400">
                        {new Date(insp.inspection_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Create-maintenance form */}
          <div className="rounded-xl bg-white p-6 shadow-lg">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">
              Log Maintenance Action
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

            <form onSubmit={handleCreateMaintenance} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Asset ID <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formAssetId}
                  onChange={(e) => setFormAssetId(e.target.value)}
                  placeholder="e.g. C1-P-001"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Maintenance Details <span className="text-rose-500">*</span>
                </label>
                <textarea
                  required
                  rows={3}
                  value={formDetails}
                  onChange={(e) => setFormDetails(e.target.value)}
                  placeholder="Describe the work performed…"
                  className="mt-1 block w-full rounded-lg border border-slate-300 p-2.5 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Status <span className="text-rose-500">*</span>
                </label>
                <select
                  value={formStatus}
                  onChange={(e) => setFormStatus(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                >
                  {['Scheduled', 'In Progress', 'Completed', 'Deferred'].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">
                  Notes (Optional)
                </label>
                <input
                  type="text"
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  placeholder="Additional observations…"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <button
                type="submit"
                disabled={formLoading}
                className="w-full rounded-lg bg-cyan-600 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-cyan-700 disabled:opacity-50"
              >
                {formLoading ? 'Saving…' : 'Log Maintenance'}
              </button>
            </form>
          </div>
        </div>

        {/* Bottom: Maintenance records table */}
        <div className="rounded-xl bg-white p-6 shadow-lg">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              All Maintenance Records
            </h2>
            <button
              onClick={fetchRecords}
              className="text-xs font-medium text-cyan-600 hover:underline"
            >
              Refresh
            </button>
          </div>

          {recordsLoading && (
            <p className="text-sm text-slate-400">Loading records…</p>
          )}
          {recordsError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {recordsError}
            </div>
          )}
          {!recordsLoading && records.length === 0 && !recordsError && (
            <p className="text-sm text-slate-400">No maintenance records yet.</p>
          )}

          {records.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    <th className="pb-2 pr-4">ID</th>
                    <th className="pb-2 pr-4">Asset</th>
                    <th className="pb-2 pr-4">Details</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 pr-4">Date</th>
                    <th className="pb-2">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {records.map((rec) => (
                    <tr key={rec.maintenance_id} className="hover:bg-slate-50">
                      <td className="py-2 pr-4 font-mono text-xs text-slate-500">
                        #{rec.maintenance_id}
                      </td>
                      <td className="py-2 pr-4 font-medium text-slate-800">
                        {rec.asset?.name || rec.asset_id}
                      </td>
                      <td className="max-w-xs py-2 pr-4 text-slate-600 truncate">
                        {rec.maintenance_details}
                      </td>
                      <td className="py-2 pr-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                            rec.status === 'Completed'
                              ? 'bg-emerald-100 text-emerald-800'
                              : rec.status === 'In Progress'
                              ? 'bg-blue-100 text-blue-800'
                              : rec.status === 'Deferred'
                              ? 'bg-rose-100 text-rose-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {rec.status}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-xs text-slate-500">
                        {new Date(rec.maintenance_date).toLocaleDateString()}
                      </td>
                      <td className="py-2 text-xs text-slate-500">
                        {rec.notes || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
