import React from 'react';
import { ShieldAlert, Zap, Lock, Siren } from 'lucide-react';

const Risk = () => {
  return (
    <div className="space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-danger">Risk Management</h1>
          <p className="text-secondary mt-1">Circuit breakers and real-time exposure control</p>
        </div>
        <button className="bg-danger hover:bg-danger/80 text-white px-8 py-4 rounded-xl font-black text-xl flex items-center gap-3 animate-pulse uppercase tracking-tighter">
          <Siren size={24} />
          Emergency Kill Switch
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Master Status */}
        <div className="glass-card p-8 flex flex-col items-center text-center border-t-4 border-t-success">
          <div className="p-4 rounded-full bg-success/10 text-success mb-4">
            <Zap size={48} />
          </div>
          <h3 className="text-2xl font-bold mb-2 uppercase tracking-widest">Operational</h3>
          <p className="text-secondary text-sm">All safety systems are nominal. Strategies are executing within bounds.</p>
        </div>

        {/* Daily Loss Breaker */}
        <div className="glass-card p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="font-bold text-lg">Daily Loss Limit</h3>
              <p className="text-xs text-secondary mt-1">Halt strategy at 2% daily loss</p>
            </div>
            <Lock size={18} className="text-secondary" />
          </div>
          <div className="relative h-4 bg-white/5 rounded-full overflow-hidden mb-4">
             <div className="absolute left-0 top-0 bottom-0 bg-primary rounded-full transition-all duration-1000" style={{ width: '42%' }} />
          </div>
          <div className="flex justify-between font-mono text-sm">
            <span>₹45,200 (Current)</span>
            <span className="text-secondary">₹1,00,000 (Limit)</span>
          </div>
        </div>

        {/* Leverage / Exposure */}
        <div className="glass-card p-6">
           <h3 className="font-bold text-lg mb-4">Exposure Distribution</h3>
           <div className="space-y-4">
             {[
               { name: 'Equity Long', val: 75, color: 'bg-primary' },
               { name: 'Options Short', val: 15, color: 'bg-warning' },
               { name: 'Cash Reserve', val: 10, color: 'bg-secondary' },
             ].map(item => (
               <div key={item.name}>
                 <div className="flex justify-between text-xs mb-1">
                   <span>{item.name}</span>
                   <span className="font-bold">{item.val}%</span>
                 </div>
                 <div className="h-1.5 bg-white/5 rounded-full">
                   <div className={`${item.color} h-full rounded-full`} style={{ width: `${item.val}%` }} />
                 </div>
               </div>
             ))}
           </div>
        </div>
      </div>

      <div className="glass-card p-6">
        <h2 className="font-bold text-xl mb-6">Constraint Violation Log</h2>
        <div className="space-y-4">
          <div className="flex items-center gap-4 p-4 bg-white/5 rounded-lg border-l-4 border-l-warning">
            <ShieldAlert className="text-warning flex-shrink-0" />
            <div>
              <div className="font-bold">Position Size Alert: TCS</div>
              <div className="text-xs text-secondary">Suggested qty exceeded sector limit of 25%. Auto-clamped to 12 shares.</div>
            </div>
            <div className="ml-auto text-xs text-secondary">2 mins ago</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Risk;
