import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Nav from '../components/Nav';
import api from '../services/api';

export default function Manager() {
  const { user } = useAuth();
  const [scores, setScores] = useState({ ahs: [], rs: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const token = localStorage.getItem('aq_token');
        const data = await api.getAnalyticsDashboard(token);
        setScores(data);
      } catch (err) {
        console.error(err);
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
            {loading ? <p>Loading...</p> : (
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
            {loading ? <p>Loading...</p> : (
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