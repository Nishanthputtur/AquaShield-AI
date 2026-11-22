import { useEffect, useState } from 'react';
function LoadingMessage({ text = 'Loading...' }) {
  return (
    <p className="text-xs text-slate-500 p-4 bg-slate-50 rounded-lg text-center">
      {text}
    </p>
  );
}

function UnavailableMessage({ text = 'Data unavailable' }) {
  return (
    <p className="text-xs text-slate-500 p-4 bg-slate-50 rounded-lg text-center">
      {text}
    </p>
  );
}
export default function App() {
  const [view, setView] = useState('home');

  // Location filter state
  const [cities, setCities] = useState([]);
  const [selectedCityId, setSelectedCityId] = useState('');
  const [zones, setZones] = useState([]);
  const [selectedZoneId, setSelectedZoneId] = useState('');

  // Live dashboard states
  const [supplyStatus, setSupplyStatus] = useState(null);
  const [waterQuality, setWaterQuality] = useState(null);
  // null = unavailable / not-yet-loaded; [] = successful response with no records.
  const [issues, setIssues] = useState(null);
  const [maintenance, setMaintenance] = useState(null);
  const [infrastructure, setInfrastructure] = useState(null);
  const [notifications, setNotifications] = useState(null);
  const [notificationsLoading, setNotificationsLoading] = useState(true);
  // Single loading flag for all area-dependent data.
  const [loading, setLoading] = useState(true);

  // Complaint form state
  const [details, setDetails] = useState('');
  const [complaintZoneId, setComplaintZoneId] = useState('');
  const [submittedId, setSubmittedId] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Complaint tracking state
  const [trackingId, setTrackingId] = useState('');
  const [trackedData, setTrackedData] = useState(null);
  const [trackError, setTrackError] = useState('');
  const [trackingLoading, setTrackingLoading] = useState(false);

  // 1. Initial load: cities, zones, notifications
  useEffect(() => {
    fetch('/api/v1/public/cities')
      .then((res) => res.json())
      .then((data) => setCities(data || []))
      .catch((err) => console.error('Failed to load cities:', err));

    fetch('/api/v1/public/zones')
      .then((res) => res.json())
      .then((data) => setZones(data || []))
      .catch((err) => console.error('Failed to load zones:', err));

    fetch('/api/v1/public/notifications')
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => setNotifications(data || []))
      .catch((err) => {
        console.error('Failed to load announcements:', err);
        setNotifications(null);
      })
  .finally(() => setNotificationsLoading(false));
  }, []);

  // 2. Fetch area-specific data whenever selectedCityId or selectedZoneId changes.
  // Uses an AbortController so that an older in-flight request cannot overwrite
  // newer area data, and cannot clear the loading flag while a newer request runs.
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    const params = new URLSearchParams();

    if (selectedCityId) params.append('city_id', selectedCityId);
    if (selectedZoneId) params.append('zone_id', selectedZoneId);

    const query = params.toString() ? `?${params.toString()}` : '';

    const fetchData = async (url) => {
      const response = await fetch(url, { signal });

      if (!response.ok) {
        return null;
      }

      return response.json();
    };

    Promise.all([
      fetchData(`/api/v1/public/status${query}`),
      fetchData(`/api/v1/public/water-quality${query}`),
      fetchData(`/api/v1/public/issues${query}`),
      fetchData(`/api/v1/public/maintenance${query}`),
      fetchData(`/api/v1/public/infrastructure${query}`),
    ])
      .then(([statusData, wqData, issuesData, maintData, infraData]) => {
        if (signal.aborted) return;

        setSupplyStatus(statusData);
        setWaterQuality(wqData);
        setIssues(issuesData);
        setMaintenance(maintData);
        setInfrastructure(infraData);
      })
      .catch((err) => {
        if (signal.aborted || err.name === 'AbortError') return;

        console.error('Error fetching area data:', err);

        setSupplyStatus(null);
        setWaterQuality(null);
        setIssues(null);
        setMaintenance(null);
        setInfrastructure(null);
      })
      .finally(() => {
        if (!signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [selectedCityId, selectedZoneId]);

  // Clear previously loaded area data so the UI never displays stale values
  // while a new area request is in flight.
  const clearAreaData = () => {
    setLoading(true);
    setSupplyStatus(null);
    setWaterQuality(null);
    setIssues(null);
    setMaintenance(null);
    setInfrastructure(null);
  };

  // Handle city selection change
  const handleCityChange = (cityId) => {
    clearAreaData();
    setSelectedCityId(cityId);
    setSelectedZoneId(''); // Reset zone when city changes
  };

  // Filter available zones for the current city
  const filteredZones = selectedCityId
    ? zones.filter((z) => String(z.city_id) === String(selectedCityId))
    : zones;

  // Submit Complaint
  const submitComplaint = async (e) => {
    e.preventDefault();
    setSubmitError('');
    if (!details.trim() || details.trim().length < 5) {
      setSubmitError('Please enter at least 5 characters describing the water issue.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        details: details.trim(),
        zone_id: complaintZoneId ? parseInt(complaintZoneId, 10) : null,
      };

      const res = await fetch('/api/v1/public/complaints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to submit complaint.');
      }

      if (data.tracking_id) {
        setSubmittedId(data.tracking_id);
      } else {
        setSubmitError("Backend didn't return a tracking ID.");
      }
    } catch (err) {
      console.error(err);
      setSubmitError(err.message || 'Failed to submit complaint! Check backend connection.');
    } finally {
      setSubmitting(false);
    }
  };

  // Track Complaint (accepts an optional override so the freshly-submitted ID can be used
  // immediately, before React commits the setTrackingId state update).
  const trackComplaint = async (e, trackingIdOverride) => {
    if (e) e.preventDefault();

    const cleanId = (trackingIdOverride ?? trackingId).trim();
    if (!cleanId) return;

    setTrackError('');
    setTrackedData(null);
    setTrackingLoading(true);

    try {
      const res = await fetch(`/api/v1/public/complaints/${encodeURIComponent(cleanId)}`);
      if (res.ok) {
        const data = await res.json();
        setTrackedData(data);
      } else if (res.status === 404) {
        setTrackedData({ error: 'No complaint found matching this Tracking ID. Please verify the ID.' });
      } else {
        setTrackedData({ error: `Server error: ${res.status}` });
      }
    } catch (err) {
      console.error(err);
      setTrackError('Could not connect to tracking service. Please try again.');
    } finally {
      setTrackingLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 flex flex-col">
      {/* Public Header */}
      <header className="bg-cyan-900 text-white shadow-md sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex flex-col sm:flex-row justify-between items-center gap-3">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setView('home')}>
            <div className="w-8 h-8 rounded-lg bg-cyan-500 flex items-center justify-center font-bold text-white shadow-sm">
              AQ
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">AquaShield Public Portal</h1>
              <p className="text-xs text-cyan-200">Simulated Water Information &amp; Citizen Services</p>
            </div>
          </div>

          <nav className="flex flex-wrap gap-1 text-sm font-medium">
            <button
              onClick={() => setView('home')}
              className={`px-3 py-1.5 rounded-md transition ${view === 'home' ? 'bg-cyan-700 text-white' : 'text-cyan-100 hover:bg-cyan-800'}`}
            >
              Overview &amp; Status
            </button>
            <button
              onClick={() => setView('quality')}
              className={`px-3 py-1.5 rounded-md transition ${view === 'quality' ? 'bg-cyan-700 text-white' : 'text-cyan-100 hover:bg-cyan-800'}`}
            >
              Simulated pH Assessment
            </button>
            <button
              onClick={() => setView('infrastructure')}
              className={`px-3 py-1.5 rounded-md transition ${view === 'infrastructure' ? 'bg-cyan-700 text-white' : 'text-cyan-100 hover:bg-cyan-800'}`}
            >
              Infrastructure &amp; Maintenance
            </button>
            <button
              onClick={() => setView('complaint')}
              className={`px-3 py-1.5 rounded-md transition ${view === 'complaint' ? 'bg-cyan-700 text-white' : 'text-cyan-100 hover:bg-cyan-800'}`}
            >
              File a Complaint
            </button>
            <button
              onClick={() => setView('track')}
              className={`px-3 py-1.5 rounded-md transition ${view === 'track' ? 'bg-cyan-700 text-white' : 'text-cyan-100 hover:bg-cyan-800'}`}
            >
              Track Complaint
            </button>
          </nav>
        </div>
      </header>

      {/* Main Body */}
      <main className="max-w-6xl mx-auto w-full px-4 py-6 flex-1">
        {/* Area Selection Bar (Visible on dashboard views) */}
        {['home', 'quality', 'infrastructure'].includes(view) && (
          <div className="mb-6 bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Selected Location:</span>
              <span className="text-sm font-semibold text-cyan-900">
                {loading
                  ? 'Loading selected area...'
                  : supplyStatus?.area_name || 'Area information unavailable'}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              {/* City Selector */}
              <div className="flex items-center space-x-1.5 flex-1 sm:flex-initial">
                <label className="text-xs font-medium text-slate-600">City:</label>
                <select
                  value={selectedCityId}
                  onChange={(e) => handleCityChange(e.target.value)}
                  className="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-cyan-500"
                >
                  <option value="">All Cities (4 Total)</option>
                  {cities.map((c) => (
                    <option key={c.city_id} value={c.city_id}>
                      {c.city_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Zone Selector */}
              <div className="flex items-center space-x-1.5 flex-1 sm:flex-initial">
                <label className="text-xs font-medium text-slate-600">Zone:</label>
                <select
                  value={selectedZoneId}
                  onChange={(e) => {
                    clearAreaData();
                    setSelectedZoneId(e.target.value);
                  }}
                  className="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-cyan-500"
                >
                  <option value="">All Zones {selectedCityId ? 'in City' : '(16 Total)'}</option>
                  {filteredZones.map((z) => (
                    <option key={z.zone_id} value={z.zone_id}>
                      {z.name} {z.city_name ? `(${z.city_name})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              {(selectedCityId || selectedZoneId) && (
                <button
                  onClick={() => {
                    clearAreaData();
                    setSelectedCityId('');
                    setSelectedZoneId('');
                  }}
                  className="text-xs text-cyan-700 hover:text-cyan-900 underline font-medium"
                >
                  Reset Area
                </button>
              )}
            </div>
          </div>
        )}

        {/* VIEW 1: HOME & WATER SUPPLY STATUS */}
        {view === 'home' && (
          <div className="space-y-6">
            {/* Water Supply Status Hero Card */}
            <div
              className={`p-5 rounded-xl border shadow-sm transition ${
                loading || !supplyStatus
                  ? 'bg-slate-50 border-slate-300 text-slate-800'
                  : supplyStatus.status === 'Normal'
                  ? 'bg-emerald-50/70 border-emerald-300 text-emerald-950'
                  : supplyStatus.status === 'Advisory'
                  ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                  : supplyStatus.status === 'Maintenance'
                  ? 'bg-blue-50/70 border-blue-300 text-blue-950'
                  : 'bg-rose-50/70 border-rose-300 text-rose-950'
              }`}
            >
              {loading ? (
                <LoadingMessage text="Loading water supply status..." />
              ) : !supplyStatus ? (
                <UnavailableMessage text="Water supply status data unavailable" />
              ) : (
                <>
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-2">
                    <div className="flex items-center space-x-2.5">
                      <span
                        className={`inline-block w-3.5 h-3.5 rounded-full animate-pulse ${
                          supplyStatus.status === 'Normal'
                            ? 'bg-emerald-500'
                            : supplyStatus.status === 'Advisory'
                            ? 'bg-amber-500'
                            : supplyStatus.status === 'Maintenance'
                            ? 'bg-blue-500'
                            : 'bg-rose-500'
                        }`}
                      />
                      <h2 className="text-xl font-bold tracking-tight">
                        Water Supply Status: {supplyStatus.status}
                      </h2>
                    </div>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-white/80 border border-slate-200">
                      {supplyStatus.area_name}
                    </span>
                  </div>
                  <p className="text-sm font-medium opacity-90">{supplyStatus.message}</p>
                </>
              )}
            </div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-xs text-slate-500 font-medium block">Monitored Assets</span>
                <span className="text-2xl font-bold text-slate-800">
                  {loading ? (
                    <span className="text-base font-normal text-slate-500">Loading...</span>
                  ) : supplyStatus ? (
                    `${supplyStatus.operational_assets} / ${supplyStatus.total_assets}`
                  ) : (
                    <span className="text-base font-normal text-slate-500">Data unavailable</span>
                  )}
                </span>
                <span className="text-xs block mt-0.5 font-medium text-slate-500">
                  {loading
                    ? 'Loading...'
                    : supplyStatus
                      ? 'Operational assets'
                      : 'Data unavailable'}
                </span>
              </div>

              <div
                className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm cursor-pointer hover:border-cyan-300 transition"
                onClick={() => setView('quality')}
              >
                <span className="text-xs text-slate-500 font-medium block">Simulated pH Assessment</span>
                <span className="text-2xl font-bold text-cyan-700">
                  {loading
                    ? 'Loading...'
                    : waterQuality
                    ? `${waterQuality.ph_value.toFixed(2)} pH`
                    : 'Unavailable'}
                </span>
                <span
                  className={`text-xs block mt-0.5 font-medium ${
                    loading || !waterQuality
                      ? 'text-slate-500'
                      : waterQuality.is_safe
                      ? 'text-emerald-600'
                      : 'text-rose-600'
                  }`}
                >
                  {loading
                    ? 'Loading...'
                    : waterQuality
                    ? `${waterQuality.status} (Project reference: 6.5–8.5)`
                    : 'No simulated pH reading available'}
                </span>
              </div>

              <div
                className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm cursor-pointer hover:border-cyan-300 transition"
                onClick={() => setView('infrastructure')}
              >
                <span className="text-xs text-slate-500 font-medium block">Listed Active Issues</span>
                <span className={`text-2xl font-bold ${
                  !loading && issues?.length > 0 ? 'text-amber-600' : 'text-slate-800'
                }`}>
                  {loading ? (
                    <span className="text-base font-normal text-slate-500">Loading...</span>
                  ) : issues === null ? (
                    <span className="text-base font-normal text-slate-500">Unavailable</span>
                  ) : (
                    issues.length
                  )}
                </span>
                <span className="text-xs text-slate-500 block mt-0.5">
                  {loading
                    ? 'Loading...'
                    : issues === null
                    ? 'Data unavailable'
                    : issues.length > 0
                    ? 'Anomalies in selected area'
                    : 'None listed'}
                </span>
              </div>

              <div
                className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm cursor-pointer hover:border-cyan-300 transition"
                onClick={() => setView('infrastructure')}
              >
                <span className="text-xs text-slate-500 font-medium block">Listed Maintenance</span>
                <span className="text-2xl font-bold text-slate-800">
                  {loading ? (
                    <span className="text-base font-normal text-slate-500">Loading...</span>
                  ) : maintenance === null ? (
                    <span className="text-base font-normal text-slate-500">Unavailable</span>
                  ) : (
                    maintenance.length
                  )}
                </span>
                <span className="text-xs text-slate-500 block mt-0.5">
                  {loading
                    ? 'Loading...'
                    : maintenance === null
                    ? 'Data unavailable'
                    : 'Work orders in selected area'}
                </span>
              </div>
            </div>

            {/* Public Announcements & Notifications */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center justify-between">
                <span>Platform Announcements &amp; Notices</span>
                <span className="text-xs text-cyan-600 font-normal">Latest platform notices</span>
              </h3>

              {notificationsLoading ? (
                <LoadingMessage text="Loading announcements..." />) :
                notifications === null ? (<UnavailableMessage text="Announcements unavailable" />)
                  : notifications.length === 0 ? (<p className="text-xs text-slate-500">
                    No public notices issued at this time.</p>) :
                    (
                      <div className="space-y-3">
                        {notifications.map((n) => (
                          <div
                            key={n.notification_id}
                            className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-slate-50 transition">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="text-sm font-semibold text-slate-900">
                                {n.title}
                              </span>
                              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-cyan-100 text-cyan-800">
                                {n.notification_type}
                              </span>
                            </div>
                            <p className="text-xs text-slate-600">{n.message}</p>
                            <span className="text-[11px] text-slate-400 mt-2 block">
                              Published: {new Date(n.created_at).toLocaleString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    )
              }
            </div>

            {/* Quick Action Links */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                onClick={() => setView('complaint')}
                className="bg-gradient-to-r from-cyan-900 to-cyan-800 text-white p-5 rounded-xl cursor-pointer hover:shadow-md transition flex justify-between items-center"
              >
                <div>
                  <h4 className="text-base font-bold">Have a Water Supply or Quality Issue?</h4>
                  <p className="text-xs text-cyan-200 mt-1">Submit an online citizen complaint. Zone selection is optional.</p>
                </div>
                <span className="bg-cyan-500 text-white text-xs font-bold px-3 py-2 rounded-lg">File Report &rarr;</span>
              </div>

              <div
                onClick={() => setView('track')}
                className="bg-gradient-to-r from-slate-800 to-slate-700 text-white p-5 rounded-xl cursor-pointer hover:shadow-md transition flex justify-between items-center"
              >
                <div>
                  <h4 className="text-base font-bold">Already Filed a Complaint?</h4>
                  <p className="text-xs text-slate-300 mt-1">View the stored complaint and its associated information using your unique Tracking ID.</p>
                </div>
                <span className="bg-slate-600 text-white text-xs font-bold px-3 py-2 rounded-lg">Track &rarr;</span>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: SIMULATED pH ASSESSMENT */}
        {view === 'quality' && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Simulated pH Assessment</h2>
                  <p className="text-xs text-slate-500">
                    Latest simulated pH reading from the project&apos;s virtual sensor data.
                  </p>
                </div>
                <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-cyan-100 text-cyan-800">
                  Configured Project Reference Range (6.5–8.5)
                </span>
              </div>

              <p className="text-xs text-slate-500 mb-4">
                The result on this page is a simulated pH assessment against the project&apos;s configured reference range. A pH reading within this range does not by itself establish overall drinking-water safety.
              </p>

              {loading ? (
                <p className="text-sm text-slate-500 p-4 bg-slate-50 rounded-lg text-center">
                  Loading simulated pH data...
                </p>
              ) : !waterQuality ? (
                <p className="text-sm text-slate-500 p-4 bg-slate-50 rounded-lg text-center">
                  No simulated pH reading is available for the selected area.
                </p>
              ) : (
                <div className="space-y-6">
                  {/* Gauge Card */}
                  <div className="p-6 rounded-xl bg-slate-50 border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="text-center md:text-left">
                      <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">Latest simulated pH reading</span>
                      <div className="text-5xl font-extrabold text-cyan-700 my-1">
                        {waterQuality.ph_value.toFixed(2)}{' '}
                        <span className="text-lg font-normal text-slate-500">pH</span>
                      </div>
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${
                          waterQuality.is_safe ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {waterQuality.status}
                      </span>
                    </div>

                    <div className="flex-1 w-full max-w-md">
                      <div className="text-xs text-slate-600 flex justify-between font-semibold mb-1">
                        <span>Acidic (&lt; 6.5)</span>
                        <span className="text-emerald-700">Project reference range (6.5 – 8.5)</span>
                        <span>Alkaline (&gt; 8.5)</span>
                      </div>
                      {/* Visual pH Scale Bar */}
                      <div className="w-full h-4 rounded-full bg-gradient-to-r from-red-400 via-emerald-400 to-purple-400 relative overflow-hidden shadow-inner">
                        <div
                          className="absolute top-0 bottom-0 w-1.5 bg-black border border-white"
                          style={{
                            left: `${Math.max(0, Math.min(100, ((waterQuality.ph_value - 4) / (11 - 4)) * 100))}%`,
                          }}
                        />
                      </div>
                      <div className="text-[11px] text-slate-500 mt-2 flex justify-between">
                        <span>Min Threshold: {waterQuality.threshold_min} pH</span>
                        <span>Max Threshold: {waterQuality.threshold_max} pH</span>
                      </div>
                    </div>
                  </div>

                  {/* Details Card */}
                  <div className="border-t border-slate-200 pt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div>
                      <span className="font-semibold text-slate-500 block">Sample Source (simulated):</span>
                      <span className="text-slate-800 font-medium">{waterQuality.sample_asset}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500 block">Assessment Message:</span>
                      <span className="text-slate-800 font-medium">{waterQuality.message}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500 block">Latest simulated reading time:</span>
                      <span className="text-slate-800 font-medium">
                        {new Date(waterQuality.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 3: INFRASTRUCTURE & MAINTENANCE & ISSUES */}
        {view === 'infrastructure' && (
          <div className="space-y-6">
            {/* Infrastructure Breakdown Card */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h2 className="text-xl font-bold text-slate-900 mb-1">Simulated Water Infrastructure</h2>
              <p className="text-xs text-slate-500 mb-4">
                {loading
                  ? 'Loading selected area...'
                  : `Virtual distribution network assets in ${
                      supplyStatus?.area_name || 'selected area'
                    }.`}
              </p>

              {loading ? (
                <LoadingMessage text="Loading infrastructure data..." />
              ) : !infrastructure ? (
                <UnavailableMessage text="Infrastructure data unavailable" />
              ) : (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
                    {Object.entries(infrastructure.type_counts || {}).map(([type, count]) => (
                      <div key={type} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                        <span className="text-xs font-semibold text-slate-600 block">{type}</span>
                        <span className="text-xl font-bold text-slate-900">{count}</span>
                      </div>
                    ))}
                  </div>

                  <div className="border-t border-slate-200 pt-4">
                    <h3 className="text-sm font-bold text-slate-800 mb-2">Asset Inventory Overview</h3>
                    {infrastructure.assets && infrastructure.assets.length > 0 ? (
                      <div className="max-h-60 overflow-y-auto border border-slate-200 rounded-lg">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-100 text-slate-700 font-semibold sticky top-0">
                            <tr>
                              <th className="p-2.5">Asset Identifier</th>
                              <th className="p-2.5">Type</th>
                              <th className="p-2.5">Location</th>
                              <th className="p-2.5">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {infrastructure.assets.slice(0, 30).map((a) => (
                              <tr key={a.asset_id} className="hover:bg-slate-50">
                                <td className="p-2.5 font-medium text-slate-900">{a.asset_id}</td>
                                <td className="p-2.5 text-slate-600">{a.type}</td>
                                <td className="p-2.5 text-slate-600">
                                  {a.zone_name} ({a.city_name})
                                </td>
                                <td className="p-2.5">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                      a.status.toLowerCase() === 'operational'
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : 'bg-amber-100 text-amber-800'
                                    }`}
                                  >
                                    {a.status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 p-4 bg-slate-50 rounded-lg text-center">
                        No assets found for the selected area.
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Operational Issues & Maintenance Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Area Issues */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-base font-bold text-slate-900 mb-3 flex items-center justify-between">
                  <span>Reported Area Issues</span>
                  <span className="text-xs text-slate-500 font-normal">Listed in selected area</span>
                </h3>
                {loading ? (
                  <LoadingMessage text="Loading active issues..." />
                ) : issues === null ? (
                  <UnavailableMessage text="Active issues data unavailable" />
                ) : issues.length === 0 ? (
                  <p className="text-xs text-slate-500 p-4 bg-slate-50 rounded-lg text-center">
                    No records found for this selected area.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {issues.map((issue) => (
                      <div key={issue.anomaly_id} className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs">
                        <div className="flex justify-between font-semibold text-slate-900 mb-1">
                          <span>{issue.asset_name}</span>
                          <span className="text-amber-700">{issue.anomaly_type}</span>
                        </div>
                        <p className="text-slate-600">{issue.description || 'Operational anomaly observed.'}</p>
                        <span className="text-[11px] text-slate-400 mt-1 block">
                          Detected: {new Date(issue.detected_at).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Maintenance Information */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-base font-bold text-slate-900 mb-3 flex items-center justify-between">
                  <span>Scheduled Maintenance</span>
                  <span className="text-xs text-slate-500 font-normal">Listed in selected area</span>
                </h3>
                {loading ? (
                  <LoadingMessage text="Loading maintenance data..." />
                ) : maintenance === null ? (
                  <UnavailableMessage text="Maintenance data unavailable" />
                ) : maintenance.length === 0 ? (
                  <p className="text-xs text-slate-500 p-4 bg-slate-50 rounded-lg text-center">
                    No records found for this selected area.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {maintenance.map((m) => (
                      <div key={m.maintenance_id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
                        <div className="flex justify-between font-semibold text-slate-900 mb-1">
                          <span>{m.asset_name}</span>
                          <span className="text-blue-700 bg-blue-100 px-2 py-0.5 rounded font-semibold">{m.status}</span>
                        </div>
                        <p className="text-slate-700 font-medium">{m.maintenance_details}</p>
                        {m.notes && <p className="text-slate-500 mt-1">Notes: {m.notes}</p>}
                        <span className="text-[11px] text-slate-400 mt-1 block">
                          Scheduled: {new Date(m.maintenance_date).toLocaleDateString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* VIEW 4: FILE A COMPLAINT */}
        {view === 'complaint' && (
          <div className="max-w-2xl mx-auto bg-white p-6 sm:p-8 rounded-xl border border-slate-200 shadow-sm">
            <h2 className="text-2xl font-bold text-slate-900 mb-1">File a Public Water Complaint</h2>
            <p className="text-xs text-slate-500 mb-6">
              Report pipe leaks, low pressure, discolored water, or service interruptions. Zone selection is optional.
            </p>

            {submittedId ? (
              <div className="p-6 bg-emerald-50 border border-emerald-200 text-emerald-950 rounded-xl space-y-4">
                <div className="flex items-center space-x-2">
                  <span className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold text-sm">
                    ✓
                  </span>
                  <h3 className="text-lg font-bold">Complaint Submitted Successfully!</h3>
                </div>
                <p className="text-xs text-slate-700">
                  Your complaint has been recorded in the AquaShield AI simulation. Save your tracking ID for future reference.
                </p>
                <div className="p-3.5 bg-white border border-emerald-300 rounded-lg flex items-center justify-between">
                  <span className="font-mono text-base font-bold text-cyan-900">{submittedId}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(submittedId)}
                    className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded border border-slate-300 font-medium"
                  >
                    Copy ID
                  </button>
                </div>

                <div className="flex space-x-3 pt-2">
                  <button
                    onClick={() => {
                      setTrackingId(submittedId);
                      setView('track');
                      trackComplaint(null, submittedId);
                    }}
                    className="bg-cyan-700 text-white text-xs font-semibold px-4 py-2 rounded-lg hover:bg-cyan-800 transition"
                  >
                    Track Status Now
                  </button>
                  <button
                    onClick={() => {
                      setSubmittedId('');
                      setDetails('');
                      setComplaintZoneId('');
                    }}
                    className="bg-slate-100 text-slate-700 text-xs font-semibold px-4 py-2 rounded-lg hover:bg-slate-200 transition border border-slate-300"
                  >
                    File Another Report
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={submitComplaint} className="space-y-4">
                {submitError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                    {submitError}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Describe the Issue <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    required
                    value={details}
                    onChange={(e) => setDetails(e.target.value)}
                      rows={4}
                      maxLength={2000}
                    className="w-full border border-slate-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-cyan-500"
                    placeholder="Describe the issue in detail (e.g., persistent water discoloration or leak near road)..."
                  />
                  <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                    <span>Minimum 5 characters</span>
                    <span>{details.length} / 2000</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Select Affected Zone <span className="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <select
                    value={complaintZoneId}
                    onChange={(e) => setComplaintZoneId(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 text-xs text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  >
                    <option value="">No specific zone / Not sure</option>
                    {zones.map((z) => (
                      <option key={z.zone_id} value={z.zone_id}>
                        {z.name} {z.city_name ? `(${z.city_name})` : ''}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Selecting a zone helps identify the affected area.
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-cyan-700 text-white font-semibold py-2.5 px-4 rounded-lg hover:bg-cyan-800 transition disabled:opacity-50 text-sm shadow-sm"
                >
                  {submitting ? 'Submitting...' : 'Submit Citizen Complaint'}
                </button>
              </form>
            )}
          </div>
        )}

        {/* VIEW 5: TRACK COMPLAINT */}
        {view === 'track' && (
          <div className="max-w-2xl mx-auto bg-white p-6 sm:p-8 rounded-xl border border-slate-200 shadow-sm">
            <h2 className="text-2xl font-bold text-slate-900 mb-1">Track Your Complaint Status</h2>
            <p className="text-xs text-slate-500 mb-6">
              Enter your unique tracking ID (e.g., CMP-7F2A1C90-3D4E) to view the stored complaint and its associated information.
            </p>

            <form onSubmit={trackComplaint} className="flex gap-2 mb-6">
              <input
                required
                value={trackingId}
                onChange={(e) => setTrackingId(e.target.value)}
                placeholder="Enter Tracking ID (e.g., CMP-8F3A2B)"
                className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono uppercase focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
              <button
                type="submit"
                disabled={trackingLoading}
                className="bg-cyan-700 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-cyan-800 transition disabled:opacity-50"
              >
                {trackingLoading ? 'Checking...' : 'Track'}
              </button>
            </form>

            {trackError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg mb-4">
                {trackError}
              </div>
            )}

            {trackedData && (
              <div
                className={`p-5 rounded-xl border ${
                  trackedData.error ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-slate-50 border-slate-200'
                }`}
              >
                {trackedData.error ? (
                  <p className="text-xs font-semibold">{trackedData.error}</p>
                ) : (
                  <div className="space-y-4 text-xs">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                      <div>
                        <span className="text-slate-400 font-semibold block text-[10px] uppercase tracking-wider">
                          Tracking ID
                        </span>
                        <span className="font-mono text-sm font-bold text-slate-900">{trackedData.tracking_id}</span>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full font-bold text-xs ${
                          trackedData.status.toLowerCase() === 'resolved'
                            ? 'bg-emerald-100 text-emerald-800'
                            : trackedData.status.toLowerCase() === 'in progress'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {trackedData.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <span className="text-slate-500 font-semibold block">Area / Zone:</span>
                        <span className="text-slate-800 font-medium">
                          {trackedData.zone_name
                            ? `${trackedData.zone_name} (${trackedData.city_name || ''})`
                            : 'Not specified (General area)'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 font-semibold block">Submitted Date:</span>
                        <span className="text-slate-800 font-medium">
                          {trackedData.submitted_at ? new Date(trackedData.submitted_at).toLocaleString() : 'Recent'}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-500 font-semibold block">Reported Issue Details:</span>
                      <p className="p-3 bg-white border border-slate-200 rounded-lg text-slate-800 mt-1 font-medium">
                        {trackedData.details}
                      </p>
                    </div>

                    <div>
                      <span className="text-slate-500 font-semibold block">Resolution Details:</span>
                      {trackedData.resolution ? (
                        <p className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-lg mt-1 font-medium">
                          {trackedData.resolution}
                        </p>
                      ) : (
                        <p className="p-3 bg-slate-100 text-slate-500 rounded-lg mt-1 italic">
                          No resolution details are currently available for this complaint.
                        </p>
                      )}
                    </div>

                    {trackedData.notifications && trackedData.notifications.length > 0 && (
                      <div className="border-t border-slate-200 pt-3">
                        <span className="text-slate-500 font-semibold block mb-2">Authority Notices:</span>
                        <div className="space-y-2">
                          {trackedData.notifications.map((n) => (
                            <div key={n.notification_id} className="p-2.5 bg-cyan-50 border border-cyan-200 rounded text-cyan-950">
                              <span className="font-bold block">{n.title}</span>
                              <span>{n.message}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 text-xs py-6 border-t border-slate-800 mt-12">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row justify-between items-center gap-2">
          <span>AquaShield AI &copy; 2026 — Simulated Water Platform (M5 Public Portal)</span>
          <span className="text-slate-500">Academic Virtual Infrastructure Prototype</span>
        </div>
      </footer>
    </div>
  );
}