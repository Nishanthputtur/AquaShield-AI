import { useState, useEffect } from 'react';
import Nav from '../components/Nav';
import api from '../services/api';

export default function Manager() {
  const [scores, setScores] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
  async function load() {
    try {
      const token = localStorage.getItem('aq_token');
      const data = await api.getAnalyticsDashboard(token);

      if (
        !data ||
        !Array.isArray(data.ahs) ||
        !Array.isArray(data.rs)
      ) {
        throw new Error('Invalid analytics dashboard response');
      }

      setScores(data);
    } catch (err) {
      console.error('Failed to load analytics dashboard:', err);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }

  load();
}, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <Nav />
      <div className="p-8 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Executive Analytics Dashboard</h1>
        <p className="text-gray-500 mb-6">Live Asset Health & Risk Overview</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-lg shadow border-t-4 border-green-500">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">Top 5 Healthiest Assets (AHS)</h2>
            {loading ? (
  <p>Loading...</p>
) : loadError ? (
  <p className="text-red-600">Analytics data unavailable.</p>
) : scores.ahs.length === 0 ? (
  <p className="text-gray-500">No asset health records available.</p>
) : (
  <ul className="space-y-3">
                {scores.ahs.slice(0, 5).map(a => (
                  <li key={a.asset_id} className="flex justify-between border-b pb-2">
                    <span className="font-medium text-gray-600">Asset {a.asset_id}</span>
                    <span className="text-green-600 font-bold">{a.score} / 100</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="bg-white p-6 rounded-lg shadow border-t-4 border-red-500">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">Top 5 Highest Risk Assets (RS)</h2>
           {loading ? (
  <p>Loading...</p>
) : loadError ? (
  <p className="text-red-600">Analytics data unavailable.</p>
) : scores.rs.length === 0 ? (
  <p className="text-gray-500">No asset risk records available.</p>
) : (
  <ul className="space-y-3">
                {scores.rs.slice(0, 5).map(r => (
                  <li key={r.asset_id} className="flex justify-between border-b pb-2">
                    <span className="font-medium text-gray-600">Asset {r.asset_id}</span>
                    <span className="text-red-500 font-bold">{r.score} / 100</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}