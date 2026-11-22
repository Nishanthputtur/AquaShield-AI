import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { roleHome } from '../utils/roleHome';
import { useAuth }from '../contexts/AuthContextStore';

export default function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getNavLinks = () => {
    if (!user) return [];
    switch (user.role) {
      case 'Administrator':
        return [{ label: 'Users', to: '/admin' }];
      case 'Engineer':
        return [{ label: 'Monitoring', to: '/engineer' }];
      case 'Maintenance Officer':
        return [
          { label: 'Inspections', to: '/maintenance' },
          { label: 'Maintenance', to: '/maintenance' },
        ];
      case 'Field Inspector':
        return [{ label: 'Inspect', to: '/inspector' }];
      case 'Utility Manager':
        return [{ label: 'Dashboard', to: '/manager' }];
      default:
        return [];
    }
  };

  const homePath = user ? roleHome(user.role) : '/login';
  const navLinks = getNavLinks();

  return (
    <header className="bg-slate-900 text-white shadow-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center space-x-8">
          <Link to={homePath} className="flex items-center space-x-2">
            <span className="text-xl font-bold tracking-tight text-cyan-400">
              AquaShield AI
            </span>
          </Link>
          <nav className="flex space-x-4">
            {navLinks.map((link, index) => (
              <Link
                key={index}
                to={link.to}
                className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        {user && (
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div className="text-sm font-medium text-slate-100">{user.name}</div>
              <div className="text-xs font-semibold text-cyan-400">{user.role}</div>
            </div>
            <button
              onClick={handleLogout}
              className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-rose-700 hover:text-white"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
