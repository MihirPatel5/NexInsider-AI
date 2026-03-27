import React, { useState } from 'react';
import TradingViewChart from '../components/TradingViewChart';
import { Search, ArrowUpCircle, ArrowDownCircle, Info } from 'lucide-react';

const Terminal = () => {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');

  const mockData = [
    { time: '2024-03-20', open: 2900, high: 2950, low: 2880, close: 2940 },
    { time: '2024-03-21', open: 2940, high: 2980, low: 2930, close: 2970 },
    { time: '2024-03-22', open: 2970, high: 3010, low: 2960, close: 3005 },
    // ... more mock bars
  ];

  return (
    <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 h-[calc(100vh-80px)]">
      {/* Left: Charting Area */}
      <div className="xl:col-span-3 flex flex-col gap-6">
        <div className="glass-card p-4 flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary" size={18} />
              <input 
                type="text" 
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="w-full bg-white/5 border border-white/10 rounded-lg py-2 pl-10 pr-4 focus:outline-none focus:border-primary transition-colors"
                placeholder="Search Symbol..."
              />
            </div>
            <div className="flex gap-4 text-sm">
               <div className="flex flex-col">
                 <span className="text-secondary text-xs uppercase">LTP</span>
                 <span className="font-bold text-success">₹2,984.50</span>
               </div>
               <div className="flex flex-col">
                 <span className="text-secondary text-xs uppercase">Change</span>
                 <span className="font-bold text-success">+1.42%</span>
               </div>
            </div>
          </div>
          <div className="flex gap-2">
            {['5m', '15m', '1h', '1d'].map(tf => (
              <button key={tf} className="px-3 py-1 rounded bg-white/5 hover:bg-white/10 text-xs font-medium uppercase">
                {tf}
              </button>
            ))}
          </div>
        </div>

        <div className="glass-card flex-1 p-2 min-h-[500px]">
          <TradingViewChart data={mockData} />
        </div>
      </div>

      {/* Right: Order Panel */}
      <div className="flex flex-col gap-6">
        <div className="glass-card p-6 flex flex-col">
          <div className="flex rounded-lg overflow-hidden border border-white/10 mb-6">
            <button 
              onClick={() => setSide('BUY')}
              className={`flex-1 py-3 font-bold transition-colors ${side === 'BUY' ? 'bg-success text-white' : 'bg-white/5 text-secondary'}`}
            >
              BUY
            </button>
            <button 
              onClick={() => setSide('SELL')}
              className={`flex-1 py-3 font-bold transition-colors ${side === 'SELL' ? 'bg-danger text-white' : 'bg-white/5 text-secondary'}`}
            >
              SELL
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-secondary uppercase font-bold mb-2 block">Order Type</label>
              <select className="w-full bg-white/5 border border-white/10 rounded-lg p-3 outline-none focus:border-primary">
                <option>Market</option>
                <option>Limit</option>
                <option>SL-Limit</option>
                <option>SL-Market</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-secondary uppercase font-bold mb-2 block">Quantity</label>
                <input type="number" defaultValue={50} className="w-full bg-white/5 border border-white/10 rounded-lg p-3 outline-none focus:border-primary" />
              </div>
              <div>
                <label className="text-xs text-secondary uppercase font-bold mb-2 block">Price</label>
                <input type="number" disabled className="w-full bg-white/5 border border-white/10 rounded-lg p-3 outline-none opacity-50" placeholder="MKT" />
              </div>
            </div>

            <div className="pt-4 border-t border-white/5">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-secondary">Req. Margin</span>
                <span className="font-mono">₹1,49,225.00</span>
              </div>
              <div className="flex justify-between text-sm mb-4">
                <span className="text-secondary">Available Balance</span>
                <span className="font-mono">₹4,50,000.00</span>
              </div>
            </div>

            <button className={`w-full py-4 rounded-xl font-bold text-lg shadow-lg shadow-primary/20 transition-transform active:scale-95 ${side === 'BUY' ? 'bg-success' : 'bg-danger'}`}>
              Place {side} Order
            </button>
          </div>
        </div>

        <div className="glass-card p-6 flex-1 overflow-hidden flex flex-col">
           <div className="flex items-center gap-2 mb-4">
             <Info size={16} className="text-primary" />
             <h3 className="font-bold">Active Position</h3>
           </div>
           <div className="flex flex-col items-center justify-center flex-1 text-secondary text-sm italic">
             No open positions for {symbol}
           </div>
        </div>
      </div>
    </div>
  );
};

export default Terminal;
