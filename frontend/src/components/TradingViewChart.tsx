import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

interface ChartProps {
  data: any[];
  signals?: any[];
}

const TradingViewChart: React.FC<ChartProps> = ({ data, signals }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      width: containerRef.current.clientWidth,
      height: 500,
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981', downColor: '#ef4444', 
      borderVisible: false, wickUpColor: '#10b981', wickDownColor: '#ef4444'
    });

    candleSeries.setData(data);
    
    // Add markers for BUY/SELL signals
    if (signals) {
      const markers = signals.map(s => ({
        time: s.time,
        position: s.signal === 'BUY' ? 'belowBar' : 'aboveBar',
        color: s.signal === 'BUY' ? '#10b981' : '#ef4444',
        shape: s.signal === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: s.signal
      }));
      candleSeries.setMarkers(markers);
    }

    const handleResize = () => {
      chart.applyOptions({ width: containerRef.current?.clientWidth });
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, signals]);

  return <div ref={containerRef} className="w-full h-full rounded-xl overflow-hidden" />;
};

export default TradingViewChart;
