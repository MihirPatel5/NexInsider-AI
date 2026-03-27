import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  BarChart3, 
  Terminal as TerminalIcon, 
  History, 
  ShieldAlert, 
  Settings,
  Activity
} from 'lucide-react';

const Sidebar = () => {
  const items = [
    { name: 'Dashboard', icon: BarChart3, path: '/' },
    { name: 'Terminal', icon: TerminalIcon, path: '/terminal' },
    { name: 'Backtest', icon: History, path: '/backtest' },
    { name: 'Risk Monitor', icon: ShieldAlert, path: '/risk' },
    { name: 'Model Health', icon: Activity, path: '/models' },
  ];

  return (
    <nav className="w-64 border-r border-white/5 bg-surface/30 p-4 flex flex-col gap-2">
      <div className="text-xl font-bold px-4 py-8 text-primary flex items-center gap-2">
        <Activity className="w-8 h-8" />
        AlgoTrade.ai
      </div>

      {items.map((item) => (
        <NavLink
          key={item.name}
          to={item.path}
          className={({ isActive }) => `
            flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
            ${isActive ? 'bg-primary/20 text-primary border-r-2 border-primary' : 'text-secondary hover:bg-white/5 hover:text-white'}
          `}
        >
          <item.icon size={20} />
          <span className="font-medium">{item.name}</span>
        </NavLink>
      ))}

      <div className="mt-auto pt-4 border-t border-white/5">
        <button className="flex items-center gap-3 px-4 py-3 text-secondary hover:text-white w-full">
          <Settings size={20} />
          <span>Settings</span>
        </button>
      </div>
    </nav>
  );
};

export default Sidebar;
