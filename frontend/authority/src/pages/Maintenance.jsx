import React from 'react';
import Nav from '../components/Nav';

export default function Maintenance() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Nav />
      <div className="mx-auto max-w-7xl p-6 sm:px-6">
        <h1 className="text-2xl font-bold text-slate-900">Maintenance Officer</h1>
        <p className="mt-2 text-slate-600">Maintenance workflows arrive Day 6.</p>
      </div>
    </div>
  );
}
