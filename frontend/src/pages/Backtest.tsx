import React from 'react';
import { Play, FileDown, LineChart, Table } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Backtest = () => {
  const mockEquityData = [
    { name: 'Jan', value: 100000 },
    { name: 'Feb', value: 105000 },
    { name: 'Mar', value: 102000 },
    { name: 'Apr', value: 115000 },
    { name: 'May', value: 121000 },
    { name: 'Jun', value: 118000 },
    { name: 'Jul', value: 135000 },
  ];

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Backtest Lab</h1>
          <p className="text-secondary mt-1">Simulate strategies on historical data</p>
        </div>
        <button className="bg-primary flex items-center gap-2 px-6 py-3 rounded-xl font-bold hover:bg-primary/80 transition-all">
          <Play size={20} />
          Run Simulation
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Config */}
        <div className="glass-card p-6 space-y-6 h-fit">
          <h2 className="font-bold text-lg border-b border-white/5 pb-2">Configuration</h2>
          
          <div className="space-y-4">
            <div>
              <label className="text-xs text-secondary uppercase font-bold mb-2 block">Strategy</label>
              <select className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-sm outline-none focus:border-primary">
                <option>Momentum Breakout v2</option>
                <option>Mean Reversion (RSI)</option>
                <option>ML Ensemble v1.0</option>
              </select>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-secondary uppercase font-bold mb-2 block">Start</label>
                <input type="date" className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-xs outline-none" />
              </div>
              <div>
                <label className="text-xs text-secondary uppercase font-bold mb-2 block">End</label>
                <input type="date" className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-xs outline-none" />
              </div>
            </div>

            <div>
              <label className="text-xs text-secondary uppercase font-bold mb-2 block">Initial Capital</label>
              <input type="text" defaultValue="₹1,00,000" className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-sm outline-none" />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Performance Chart */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-bold text-lg">Equity Curve</h2>
              <div className="flex gap-2">
                <button className="p-2 rounded hover:bg-white/5 text-secondary"><FileDown size={18} /></button>
              </div>
            </div>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockEquityData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1f2937" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v/1000}k`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#121214', border: '1px solid #1f2937', borderRadius: '8px' }}
                    itemStyle={{ color: '#3b82f6' }}
                  />
                  <Area type="monotone" dataKey="value" stroke="#3b82f6" fillOpacity={1} fill="url(#colorValue)" strokeWidth={3} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Metrics Table */}
          <div className="glass-card overflow-hidden">
            <div className="p-4 border-b border-white/5 font-bold">Key Performance Indicators</div>
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-secondary uppercase text-[10px] tracking-widest font-bold">
                <tr>
                  <th className="px-6 py-4">Metric</th>
                  <th className="px-6 py-4">Strategy</th>
                  <th className="px-6 py-4">Benchmark (Nifty 50)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {[
                  { m: 'Cumulative Return', s: '35.4%', b: '12.1%' },
                  { m: 'Sharpe Ratio', s: '2.44', b: '0.85' },
                  { m: 'Max Drawdown', s: '-8.2%', b: '-15.4%' },
                  { m: 'Win Rate', s: '62.5%', b: '-' },
                ].map((row, idx) => (
                  <tr key={idx} className="hover:bg-white/5 transition-colors">
                    <td className="px-6 py-4 font-medium text-secondary">{row.m}</td>
                    <td className="px-6 py-4 font-bold text-success">{row.s}</td>
                    <td className="px-6 py-4">{row.b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Backtest;
