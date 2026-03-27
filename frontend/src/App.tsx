import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Terminal from './pages/Terminal';
import Backtest from './pages/Backtest';
import Risk from './pages/Risk';

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-background text-white">
        <Sidebar />
        <main className="flex-1 p-6 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/terminal" element={<Terminal />} />
            <Route path="/backtest" element={<Backtest />} />
            <Route path="/risk" element={<Risk />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
