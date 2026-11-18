import React, { useState } from 'react';
import Nav from '../components/Nav';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

const EXAMPLE_ASSETS = ['C1-TF-001', 'C1-P-001', 'C1-V-001'];

export default function Inspector() {
  const { token } = useAuth();

  const [assetIdInput, setAssetIdInput] = useState('');
  const [asset, setAsset] = useState(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState('');

  const [findings, setFindings] = useState('');
  const [condition, setCondition] = useState('');
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState('');
  const [submitError, setSubmitError] = useState('');

  const handleLookup = async (idToLookup) => {
    const targetId = (idToLookup || assetIdInput).trim();
    if (!targetId) return;

    setLookupError('');
    setSubmitSuccess('');
    setSubmitError('');
    setLookupLoading(true);

    try {
      const data = await api.getAsset(token, targetId);
      setAsset(data);
    } catch (err) {
      setAsset(null);
      if (err.status === 404) {
        setLookupError('Asset not found');
      } else {
        setLookupError(err.message || 'Error looking up asset');
      }
    } finally {
      setLookupLoading(false);
    }
  };

  const handleChipClick = (id) => {
    setAssetIdInput(id);
    handleLookup(id);
  };

  const handleInspectionSubmit = async (e) => {
    e.preventDefault();
    if (!asset || !findings.trim()) return;

    setSubmitSuccess('');
    setSubmitError('');
    setSubmitLoading(true);

    try {
      const payload = {
        asset_id: asset.asset_id,
        findings: findings.trim(),
      };
      if (condition.trim()) {
        payload.condition = condition.trim();
      }

      const res = await api.createInspection(token, payload);
      setSubmitSuccess(`Inspection submitted (ID: ${res.inspection_id})`);
      setFindings('');
      setCondition('');
    } catch (err) {
      setSubmitError(
        err.detail || err.message || 'Failed to submit inspection report'
      );
    } finally {
      setSubmitLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Nav />

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Field Inspection Form
          </h1>
          <p className="text-sm text-slate-500">
            Look up municipal water assets and submit on-site physical evaluation reports
          </p>
        </div>

        {/* Asset Lookup Section */}
        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">
            Asset Identification
          </h2>

          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              value={assetIdInput}
              onChange={(e) => setAssetIdInput(e.target.value)}
              placeholder="e.g. C1-TF-001"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
            <button
              type="button"
              onClick={() => handleLookup(assetIdInput)}
              disabled={lookupLoading || !assetIdInput.trim()}
              className="rounded-lg bg-cyan-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-700 disabled:opacity-50"
            >
              {lookupLoading ? 'Searching...' : 'Look up'}
            </button>
          </div>

          <div className="mt-3 flex items-center space-x-2">
            <span className="text-xs text-slate-500">Quick select:</span>
            {EXAMPLE_ASSETS.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => handleChipClick(id)}
                className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700 hover:border-cyan-400 hover:bg-cyan-50 hover:text-cyan-800"
              >
                {id}
              </button>
            ))}
          </div>

          {lookupError && (
            <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {lookupError}
            </div>
          )}

          {asset && (
            <div className="mt-5 rounded-lg border border-cyan-100 bg-cyan-50/50 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-bold text-slate-800">
                  {asset.name}
                </span>
                <span className="rounded-full bg-cyan-600/10 px-2.5 py-0.5 text-xs font-semibold text-cyan-800">
                  {asset.status}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-4">
                <div>
                  <span className="font-semibold text-slate-500">Asset ID:</span>{' '}
                  {asset.asset_id}
                </div>
                <div>
                  <span className="font-semibold text-slate-500">Type:</span>{' '}
                  {asset.type}
                </div>
                <div>
                  <span className="font-semibold text-slate-500">City:</span>{' '}
                  {asset.city_name}
                </div>
                <div>
                  <span className="font-semibold text-slate-500">Zone:</span>{' '}
                  {asset.zone_name}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Inspection Form Section */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">
            Submit Inspection Report
          </h2>

          {submitSuccess && (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              {submitSuccess}
            </div>
          )}

          {submitError && (
            <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
              {submitError}
            </div>
          )}

          <form onSubmit={handleInspectionSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Findings <span className="text-rose-500">*</span>
              </label>
              <textarea
                required
                rows={4}
                value={findings}
                onChange={(e) => setFindings(e.target.value)}
                disabled={!asset || submitLoading}
                placeholder={
                  asset
                    ? 'Enter physical condition findings, visible anomalies, sensor alignment...'
                    : 'First look up a valid asset to enable inspection submission'
                }
                className="mt-1 block w-full rounded-lg border border-slate-300 p-2.5 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:bg-slate-100 disabled:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Condition Assessment (Optional)
              </label>
              <input
                type="text"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                disabled={!asset || submitLoading}
                placeholder="e.g. Good, Fair, Critical, Operable"
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:bg-slate-100 disabled:text-slate-400"
              />
            </div>

            <button
              type="submit"
              disabled={!asset || submitLoading || !findings.trim()}
              className="rounded-lg bg-cyan-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-cyan-700 disabled:opacity-50"
            >
              {submitLoading ? 'Submitting...' : 'Submit Inspection'}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
