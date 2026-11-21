import { useState } from 'react';

export default function App() {
  const [view, setView] = useState('home');
  const [trackingId, setTrackingId] = useState('');
  const [trackedData, setTrackedData] = useState(null);
  
  // Complaint form state
  const [details, setDetails] = useState('');
  const [submittedId, setSubmittedId] = useState('');

   const submitComplaint = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/public/complaints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ details, zone_id: null })
      });
      
      if (!res.ok) {
        throw new Error(`Server responded with status: ${res.status}`);
      }

      const data = await res.json();
      
      if (data.tracking_id) {
        setSubmittedId(data.tracking_id);
      } else {
        alert("Backend didn't return a tracking ID.");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to submit complaint! Check if the backend is running.");
    }
  };

  const trackComplaint = async (e) => {
    e.preventDefault();
    const res = await fetch(`/api/v1/public/complaints/${trackingId}`);
    if (res.ok) {
      setTrackedData(await res.json());
    } else {
      setTrackedData({ error: 'Complaint not found' });
    }
  };

  return (
    <div className="min-h-screen bg-blue-50 font-sans">
      {/* Public Header */}
      <header className="bg-blue-800 text-white p-4 shadow-md">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold tracking-wide">AquaShield Public Portal</h1>
          <nav className="space-x-4">
            <button onClick={() => setView('home')} className="hover:underline">Home</button>
            <button onClick={() => setView('complaint')} className="hover:underline">File a Complaint</button>
            <button onClick={() => setView('track')} className="hover:underline">Track Complaint</button>
          </nav>
        </div>
      </header>

      <main className="max-w-3xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-lg">
        {view === 'home' && (
          <div>
            <h2 className="text-3xl font-bold text-gray-800 mb-4">Water Supply Status</h2>
            <div className="p-4 bg-green-100 border-l-4 border-green-500 text-green-700 mb-4">
              <strong>Status: Normal.</strong> All systems operational in your area.
            </div>
            <p className="text-gray-600">
              Welcome to the AquaShield public information portal. Select your area to view localized updates, or use the menu above to file a complaint.
            </p>
          </div>
        )}

        {view === 'complaint' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">File a Complaint</h2>
            {submittedId ? (
              <div className="p-4 bg-blue-100 text-blue-800 rounded">
                <p className="font-bold">Complaint Submitted Successfully!</p>
                <p>Your Tracking ID is: <span className="font-mono text-lg font-bold">{submittedId}</span></p>
                <p className="text-sm mt-2">Please save this ID to track your complaint status.</p>
                <button onClick={() => { setSubmittedId(''); setDetails(''); }} className="mt-4 bg-blue-600 text-white px-4 py-2 rounded">File Another</button>
              </div>
            ) : (
              <form onSubmit={submitComplaint} className="space-y-4">
                <div>
                  <label className="block text-gray-700 mb-1">Describe the issue</label>
                  <textarea required value={details} onChange={e => setDetails(e.target.value)} className="w-full border p-2 rounded h-32" placeholder="E.g., Low water pressure in Zone B..."></textarea>
                </div>
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded font-bold hover:bg-blue-700">Submit Complaint</button>
              </form>
            )}
          </div>
        )}

        {view === 'track' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Track Your Complaint</h2>
            <form onSubmit={trackComplaint} className="flex gap-2 mb-6">
              <input required value={trackingId} onChange={e => setTrackingId(e.target.value)} placeholder="Enter Tracking ID (e.g., CMP-8F3A2B)" className="border p-2 rounded flex-1 font-mono uppercase" />
              <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded font-bold">Track</button>
            </form>
            
            {trackedData && (
              <div className={`p-4 rounded border ${trackedData.error ? 'bg-red-100 text-red-700' : 'bg-gray-100'}`}>
                {trackedData.error ? (
                  <p>{trackedData.error}</p>
                ) : (
                  <>
                    <p><strong>Status:</strong> <span className="bg-yellow-200 px-2 py-1 rounded text-sm">{trackedData.status}</span></p>
                    <p className="mt-2"><strong>Issue:</strong> {trackedData.details}</p>
                    {trackedData.resolution && <p className="mt-2 text-green-700"><strong>Resolution:</strong> {trackedData.resolution}</p>}
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}