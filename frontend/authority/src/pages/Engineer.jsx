import React, { useCallback, useEffect, useRef, useState } from 'react';
import Chart from '../components/Chart';
import Nav from '../components/Nav';
import { useAuth } from '../contexts/AuthContextStore';
import api from '../services/api';

const PARAMETERS = [
  'Pressure',
  'Flow Rate',
  'Water Level',
  'Water Temperature',
  'pH',
  'Turbidity',
];

export default function Engineer() {
  const { token } = useAuth();

  const [simState, setSimState] = useState({ state: 'STOPPED', tick: 0 });
  const [readings, setReadings] = useState([]);
  const [selectedParameter, setSelectedParameter] = useState('Pressure');
  const [bannerError, setBannerError] = useState('');
  const [isActionLoading, setIsActionLoading] = useState(false);

  const pollIntervalRef = useRef(null);

  // Fetch latest monitoring readings
  const fetchReadings = useCallback(async () => {
    try {
      const data = await api.getReadings(token, 328);
      if (data && data.readings) {
        setReadings(data.readings);
      }
    } catch (err) {
      // Don't crash on read errors
      setBannerError(err.message || 'Failed to fetch readings');
    }
  }, [token]);
// Initial load
useEffect(() => {
  let isMounted = true;

  async function loadInitialState() {
    try {
      const data = await api.getSimulationState(token);
      if (isMounted) {
        setSimState(data);
      }
    } catch (err) {
      if (isMounted) {
        setBannerError(err.message || 'Failed to fetch simulation state');
      }
    }
  }

  async function loadInitialReadings() {
    try {
      const data = await api.getReadings(token, 328);
      if (isMounted && data && data.readings) {
        setReadings(data.readings);
      }
    } catch (err) {
      if (isMounted) {
        setBannerError(err.message || 'Failed to fetch readings');
      }
    }
  }

  loadInitialState();
  loadInitialReadings();

  return () => {
    isMounted = false;
  };
}, [token]);

  // Auto-polling when state is RUNNING
  useEffect(() => {
    if (simState.state === 'RUNNING') {
      if (!pollIntervalRef.current) {
        pollIntervalRef.current = setInterval(async () => {
          try {
            const nextState = await api.getSimulationState(token);
            setSimState(nextState);
            if (nextState.state !== 'RUNNING') {
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
              }
              return;
            }
            const data = await api.getReadings(token, 328);
            if (data && data.readings) {
              setReadings(data.readings);
            }
          } catch (err) {
            setBannerError(err.message || 'Polling error');
          }
        }, 3000);
      }
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [simState.state, token]);

  const handleAction = async (action) => {
    setBannerError('');
    setIsActionLoading(true);
    try {
      let result;
      switch (action) {
        case 'start':
          result = await api.startSimulation(token);
          break;
        case 'pause':
          result = await api.pauseSimulation(token);
          break;
        case 'resume':
          result = await api.resumeSimulation(token);
          break;
        case 'stop':
          result = await api.stopSimulation(token);
          break;
        case 'reset':
          result = await api.resetSimulation(token);
          break;
        default:
          return;
      }

      if (result) {
        setSimState(result);
        if (result.state === 'RUNNING') {
          fetchReadings();
        }
      }
    } catch (err) {
      const msg =
        err.detail || err.message || `Action ${action} rejected (${err.status || 400})`;
      setBannerError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsActionLoading(false);
    }
  };

  const isStartDisabled = simState.state !== 'STOPPED';
  const isPauseDisabled = simState.state !== 'RUNNING';
  const isResumeDisabled = simState.state !== 'PAUSED';
  const isStopDisabled =
    simState.state !== 'RUNNING' && simState.state !== 'PAUSED';
  const isResetDisabled = false;

  const getStateBadge = () => {
    switch (simState.state) {
      case 'RUNNING':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'PAUSED':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'STOPPED':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Nav />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Simulation & Monitoring
            </h1>
            <p className="text-sm text-slate-500">
              Real-time virtual telemetry engine control and asset observation
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${getStateBadge()}`}
            >
              {simState.state}
            </span>
            <span className="rounded-lg bg-white px-3 py-1 text-xs font-semibold text-slate-600 shadow-sm border border-slate-200">
              Tick: {simState.tick}
            </span>
          </div>
        </div>

        {bannerError && (
          <div className="mb-6 flex items-center justify-between rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <span>{bannerError}</span>
            <button
              onClick={() => setBannerError('')}
              className="text-xs font-semibold text-rose-600 hover:text-rose-900"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Controls Card */}
        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">
            Engine Controls
          </h2>
          <div className="flex flex-wrap gap-2.5">
            <button
              onClick={() => handleAction('start')}
              disabled={isActionLoading}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                isStartDisabled
                  ? 'bg-emerald-50 text-emerald-400 border border-emerald-200 opacity-60'
                  : 'bg-emerald-600 text-white shadow-sm hover:bg-emerald-700'
              }`}
            >
              Start
            </button>
            <button
              onClick={() => handleAction('pause')}
              disabled={isActionLoading}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                isPauseDisabled
                  ? 'bg-amber-50 text-amber-400 border border-amber-200 opacity-60'
                  : 'bg-amber-500 text-white shadow-sm hover:bg-amber-600'
              }`}
            >
              Pause
            </button>
            <button
              onClick={() => handleAction('resume')}
              disabled={isActionLoading}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                isResumeDisabled
                  ? 'bg-blue-50 text-blue-400 border border-blue-200 opacity-60'
                  : 'bg-blue-600 text-white shadow-sm hover:bg-blue-700'
              }`}
            >
              Resume
            </button>
            <button
              onClick={() => handleAction('stop')}
              disabled={isActionLoading}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                isStopDisabled
                  ? 'bg-rose-50 text-rose-400 border border-rose-200 opacity-60'
                  : 'bg-rose-600 text-white shadow-sm hover:bg-rose-700'
              }`}
            >
              Stop
            </button>
            <button
              onClick={() => handleAction('reset')}
              disabled={isActionLoading}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                isResetDisabled
                  ? 'bg-slate-100 text-slate-400 opacity-60'
                  : 'bg-slate-700 text-white shadow-sm hover:bg-slate-800'
              }`}
            >
              Reset
            </button>
          </div>
        </div>

        {/* Telemetry Chart Section */}
        <div className="space-y-4">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Telemetry Visualization
              </h2>
              <p className="text-xs text-slate-500">
                Showing {readings.length} total readings across municipal assets
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-600">
                Parameter:
              </label>
              <select
                value={selectedParameter}
                onChange={(e) => setSelectedParameter(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                {PARAMETERS.map((param) => (
                  <option key={param} value={param}>
                    {param}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Chart readings={readings} parameter={selectedParameter} />
        </div>
      </main>
    </div>
  );
}
