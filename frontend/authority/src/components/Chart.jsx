import React, { useMemo } from 'react';
import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const COLOR_PALETTE = [
  '#06b6d4', // cyan-500
  '#3b82f6', // blue-500
  '#8b5cf6', // purple-500
  '#ec4899', // pink-500
  '#f59e0b', // amber-500
  '#10b981', // emerald-500
  '#6366f1', // indigo-500
  '#14b8a6', // teal-500
  '#f97316', // orange-500
  '#84cc16', // lime-500
];

export default function SensorChart({ readings = [], parameter = 'Pressure' }) {
  const chartData = useMemo(() => {
    if (!readings || readings.length === 0 || !parameter) {
      return null;
    }

    const filtered = readings.filter(
      (r) =>
        r.parameter &&
        r.parameter.trim().toLowerCase() === parameter.trim().toLowerCase()
    );

    if (filtered.length === 0) {
      return null;
    }

    // Extract sorted unique timestamps (up to last 30)
    const uniqueTimestamps = Array.from(
      new Set(filtered.map((r) => r.timestamp))
    )
      .sort()
      .slice(-30);

    const labels = uniqueTimestamps.map((ts) => {
      try {
        const d = new Date(ts);
        return isNaN(d.getTime()) ? ts : d.toLocaleTimeString();
      } catch {
        return ts;
      }
    });

    // Group readings by asset_id
    const assetMap = new Map();
    filtered.forEach((r) => {
      const id = r.asset_id || 'Unknown';
      if (!assetMap.has(id)) {
        const displayName = r.asset?.name || r.asset_id || id;
        assetMap.set(id, { name: displayName, byTimestamp: new Map() });
      }
      assetMap.get(id).byTimestamp.set(r.timestamp, r.value);
    });

    // Limit visible lines to prevent over-clutter if there are dozens of assets
    const assetEntries = Array.from(assetMap.entries()).slice(0, 10);

    const datasets = assetEntries.map(([, info], index) => {
      const color = COLOR_PALETTE[index % COLOR_PALETTE.length];
      const data = uniqueTimestamps.map(
        (ts) => info.byTimestamp.get(ts) ?? null
      );

      return {
        label: info.name,
        data,
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.3,
        spanGaps: true,
      };
    });

    return { labels, datasets };
  }, [readings, parameter]);

  if (!chartData || chartData.datasets.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm font-medium text-slate-400">
        Waiting for data...
      </div>
    );
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          boxWidth: 12,
          boxHeight: 12,
          font: { size: 11 },
          color: '#334155',
        },
      },
      title: {
        display: true,
        text: `${parameter} Trend Across Assets`,
        font: { size: 14, weight: '600' },
        color: '#1e293b',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 0,
          font: { size: 10 },
          color: '#64748b',
        },
        grid: {
          color: '#f1f5f9',
        },
      },
      y: {
        ticks: {
          font: { size: 10 },
          color: '#64748b',
        },
        grid: {
          color: '#f1f5f9',
        },
      },
    },
  };

  return (
    <div className="h-80 w-full rounded-xl bg-white p-4 shadow-sm border border-slate-200">
      <Line data={chartData} options={options} />
    </div>
  );
}
