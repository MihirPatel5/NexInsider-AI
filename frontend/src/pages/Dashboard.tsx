import React from 'react';
import { TrendingUp, Activity, ShieldCircle, LayoutGrid } from 'lucide-react';

const Dashboard = () => {
  const stats = [
    { name: 'Daily P&L', value: '+₹12,450', change: '+2.4%', color: 'text-success' },
    { name: 'Active Signals', value: '14', change: '-2', color: 'text-primary' },
    { name: 'Net Exposure', value: '₹4.2L', change: '85%', color: 'text-warning' },
    { name: 'Max Drawdown', value: '1.2%', change: 'Safe', color: 'text-success' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Market Overview</h1>
          <p className="text-secondary mt-1">Real-time performance and active signals</p>
        </div>
        <div className="flex gap-3">
          <div className="glass-card px-4 py-2 flex items-center gap-2 text-sm">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
            Live Market
          </div>
          <button className="bg-primary hover:bg-primary/80 transition-colors px-6 py-2 rounded-lg font-semibold">
            Deploy Strategy
          </button>
        </div>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="glass-card p-6 border-l-4 border-l-primary/30">
            <div className="text-sm text-secondary uppercase tracking-wider">{stat.name}</div>
            <div className="flex items-end justify-between mt-2">
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className={`text-sm font-medium ${stat.color}`}>{stat.change}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart Slot */}
        <div className="lg:col-span-2 glass-card p-6 h-[450px] relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <TrendingUp className="text-primary" />
              <h2 className="text-xl font-bold">Nifty 50 Performance</h2>
            </div>
          </div>
          <div className="absolute inset-0 top-20 bottom-6 px-6">
             <div className="w-full h-full bg-white/5 rounded-lg flex items-center justify-center text-secondary italic">
               (Charting Engine Initializing...)
             </div>
          </div>
        </div>

        {/* Signal Sidebar */}
        <div className="glass-card p-6">
           <div className="flex items-center gap-3 mb-6">
             <Activity className="text-primary" />
             <h2 className="text-xl font-bold">Recent Signals</h2>
           </div>
           <div className="space-y-4">
             {[1,2,3,4,5].map(i => (
               <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer">
                 <div className="flex items-center gap-3">
                   <div className="w-10 h-10 rounded bg-primary/20 flex items-center justify-center font-bold text-xs">REL</div>
                   <div>
                     <div className="font-semibold text-sm">RELIANCE</div>
                     <div className="text-xs text-secondary">Momentum • 1d</div>
                   </div>
                 </div>
                 <div className="text-right">
                   <div className="text-success font-bold text-sm">BUY</div>
                   <div className="text-xs text-secondary">88% Conf</div>
                 </div>
               </div>
             ))}
           </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
