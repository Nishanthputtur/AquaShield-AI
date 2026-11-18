import React from 'react';
import Nav from '../components/Nav';

export default function Manager() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Nav />
      <div className="mx-auto max-w-7xl p-6 sm:px-6">
        <h1 className="text-2xl font-bold text-slate-900">Utility Manager</h1>
        <p className="mt-2 text-slate-600">Executive dashboard arrives Day 6.</p>
      </div>
    </div>
  );
}
