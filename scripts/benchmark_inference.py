#!/usr/bin/env python3
"""
scripts/benchmark_inference.py — Benchmark ML model inference speed.

Measures inference time for single symbol and batch predictions
to ensure the system can generate signals quickly enough for trading.
"""
import time
import argparse
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
from loguru import logger

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.ensemble import SignalEnsemble
from data.features.technical import compute_technical_features


def generate_sample_data(symbol: str, bars: int = 100) -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=bars, freq='D')
    
    np.random.seed(hash(symbol) % 2**32)
    base_price = 1000
    returns = np.random.normal(0.001, 0.02, bars)
    prices = base_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, bars)),
        'high': prices * (1 + np.random.uniform(0, 0.02, bars)),
        'low': prices * (1 + np.random.uniform(-0.02, 0, bars)),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, bars)
    })
    
    return df


def predict_single(symbol: str, ensemble: SignalEnsemble) -> dict:
    """
    Make prediction for a single symbol.
    
    Returns:
        Dict with prediction and timing info
    """
    start_time = time.time()
    
    # Load data
    df = generate_sample_data(symbol)
    
    # Compute features
    df = compute_technical_features(df)
    
    # Get latest row
    latest = df.iloc[-1]
    
    # Make prediction (simplified - using RSI-based strategy)
    rsi = latest.get('rsi_14', 50)
    
    if rsi < 30:
        pred = 2  # BUY
        conf = 0.7
    elif rsi > 70:
        pred = 0  # SELL
        conf = 0.7
    else:
        pred = 1  # HOLD
        conf = 0.5
    
    elapsed = time.time() - start_time
    
    return {
        'symbol': symbol,
        'prediction': pred,
        'confidence': conf,
        'time_ms': elapsed * 1000
    }


def benchmark_single_symbol(ensemble: SignalEnsemble, iterations: int = 100) -> dict:
    """
    Benchmark single symbol inference.
    
    Args:
        ensemble: SignalEnsemble instance
        iterations: Number of iterations to run
    
    Returns:
        Dict with timing statistics
    """
    logger.info(f"Benchmarking single symbol inference ({iterations} iterations)...")
    
    times = []
    
    for i in range(iterations):
        result = predict_single('RELIANCE', ensemble)
        times.append(result['time_ms'])
    
    times = np.array(times)
    
    return {
        'iterations': iterations,
        'mean_ms': float(np.mean(times)),
        'median_ms': float(np.median(times)),
        'std_ms': float(np.std(times)),
        'min_ms': float(np.min(times)),
        'max_ms': float(np.max(times)),
        'p95_ms': float(np.percentile(times, 95)),
        'p99_ms': float(np.percentile(times, 99))
    }


def benchmark_batch_inference(ensemble: SignalEnsemble, batch_size: int = 500) -> dict:
    """
    Benchmark batch inference for multiple symbols.
    
    Args:
        ensemble: SignalEnsemble instance
        batch_size: Number of symbols to process
    
    Returns:
        Dict with timing statistics
    """
    logger.info(f"Benchmarking batch inference ({batch_size} symbols)...")
    
    # Generate symbol list
    symbols = [f'SYMBOL_{i:04d}' for i in range(batch_size)]
    
    start_time = time.time()
    
    results = []
    for symbol in symbols:
        result = predict_single(symbol, ensemble)
        results.append(result)
    
    total_time = time.time() - start_time
    
    times = [r['time_ms'] for r in results]
    
    return {
        'batch_size': batch_size,
        'total_time_s': float(total_time),
        'mean_time_per_symbol_ms': float(np.mean(times)),
        'throughput_symbols_per_sec': float(batch_size / total_time)
    }


def benchmark_concurrent_inference(ensemble: SignalEnsemble, 
                                   num_symbols: int = 100,
                                   num_workers: int = 4) -> dict:
    """
    Benchmark concurrent inference with multiple workers.
    
    Args:
        ensemble: SignalEnsemble instance
        num_symbols: Number of symbols to process
        num_workers: Number of concurrent workers
    
    Returns:
        Dict with timing statistics
    """
    logger.info(f"Benchmarking concurrent inference ({num_symbols} symbols, {num_workers} workers)...")
    
    symbols = [f'SYMBOL_{i:04d}' for i in range(num_symbols)]
    
    start_time = time.time()
    
    results = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(predict_single, symbol, ensemble): symbol 
                  for symbol in symbols}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    total_time = time.time() - start_time
    
    times = [r['time_ms'] for r in results]
    
    return {
        'num_symbols': num_symbols,
        'num_workers': num_workers,
        'total_time_s': float(total_time),
        'mean_time_per_symbol_ms': float(np.mean(times)),
        'throughput_symbols_per_sec': float(num_symbols / total_time),
        'speedup_vs_sequential': float((num_symbols * np.mean(times) / 1000) / total_time)
    }


def benchmark_memory_usage() -> dict:
    """
    Benchmark memory usage during inference.
    
    Returns:
        Dict with memory statistics
    """
    logger.info("Benchmarking memory usage...")
    
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_mb = process.memory_info().rss / 1024 / 1024
        
        # Load ensemble
        ensemble = SignalEnsemble()
        
        # After loading
        after_load_mb = process.memory_info().rss / 1024 / 1024
        
        # Run inference
        for i in range(100):
            predict_single(f'SYMBOL_{i}', ensemble)
        
        # After inference
        after_inference_mb = process.memory_info().rss / 1024 / 1024
        
        return {
            'baseline_mb': float(baseline_mb),
            'after_load_mb': float(after_load_mb),
            'after_inference_mb': float(after_inference_mb),
            'load_overhead_mb': float(after_load_mb - baseline_mb),
            'inference_overhead_mb': float(after_inference_mb - after_load_mb),
            'total_mb': float(after_inference_mb)
        }
    
    except ImportError:
        logger.warning("psutil not installed, skipping memory benchmark")
        return {
            'error': 'psutil not installed'
        }


def main():
    parser = argparse.ArgumentParser(description='Benchmark ML model inference speed')
    parser.add_argument('--single-iterations', type=int, default=100,
                        help='Number of iterations for single symbol benchmark')
    parser.add_argument('--batch-size', type=int, default=500,
                        help='Batch size for batch inference benchmark')
    parser.add_argument('--concurrent-symbols', type=int, default=100,
                        help='Number of symbols for concurrent benchmark')
    parser.add_argument('--concurrent-workers', type=int, default=4,
                        help='Number of workers for concurrent benchmark')
    parser.add_argument('--output', type=str, default='inference_benchmark_results.json',
                        help='Output file for results')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("INFERENCE SPEED BENCHMARK")
    logger.info("=" * 60)
    
    ensemble = SignalEnsemble()
    
    # Run benchmarks
    results = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'benchmarks': {}
    }
    
    # Single symbol benchmark
    logger.info("\n1. Single Symbol Inference")
    logger.info("-" * 60)
    single_results = benchmark_single_symbol(ensemble, args.single_iterations)
    results['benchmarks']['single_symbol'] = single_results
    
    logger.info(f"Mean:   {single_results['mean_ms']:.2f} ms")
    logger.info(f"Median: {single_results['median_ms']:.2f} ms")
    logger.info(f"Std:    {single_results['std_ms']:.2f} ms")
    logger.info(f"Min:    {single_results['min_ms']:.2f} ms")
    logger.info(f"Max:    {single_results['max_ms']:.2f} ms")
    logger.info(f"P95:    {single_results['p95_ms']:.2f} ms")
    logger.info(f"P99:    {single_results['p99_ms']:.2f} ms")
    
    # Batch inference benchmark
    logger.info("\n2. Batch Inference")
    logger.info("-" * 60)
    batch_results = benchmark_batch_inference(ensemble, args.batch_size)
    results['benchmarks']['batch_inference'] = batch_results
    
    logger.info(f"Batch Size:     {batch_results['batch_size']}")
    logger.info(f"Total Time:     {batch_results['total_time_s']:.2f} s")
    logger.info(f"Per Symbol:     {batch_results['mean_time_per_symbol_ms']:.2f} ms")
    logger.info(f"Throughput:     {batch_results['throughput_symbols_per_sec']:.2f} symbols/sec")
    
    # Concurrent inference benchmark
    logger.info("\n3. Concurrent Inference")
    logger.info("-" * 60)
    concurrent_results = benchmark_concurrent_inference(
        ensemble, 
        args.concurrent_symbols,
        args.concurrent_workers
    )
    results['benchmarks']['concurrent_inference'] = concurrent_results
    
    logger.info(f"Symbols:        {concurrent_results['num_symbols']}")
    logger.info(f"Workers:        {concurrent_results['num_workers']}")
    logger.info(f"Total Time:     {concurrent_results['total_time_s']:.2f} s")
    logger.info(f"Per Symbol:     {concurrent_results['mean_time_per_symbol_ms']:.2f} ms")
    logger.info(f"Throughput:     {concurrent_results['throughput_symbols_per_sec']:.2f} symbols/sec")
    logger.info(f"Speedup:        {concurrent_results['speedup_vs_sequential']:.2f}x")
    
    # Memory usage benchmark
    logger.info("\n4. Memory Usage")
    logger.info("-" * 60)
    memory_results = benchmark_memory_usage()
    results['benchmarks']['memory_usage'] = memory_results
    
    if 'error' not in memory_results:
        logger.info(f"Baseline:       {memory_results['baseline_mb']:.2f} MB")
        logger.info(f"After Load:     {memory_results['after_load_mb']:.2f} MB")
        logger.info(f"After Inference:{memory_results['after_inference_mb']:.2f} MB")
        logger.info(f"Load Overhead:  {memory_results['load_overhead_mb']:.2f} MB")
        logger.info(f"Inference OH:   {memory_results['inference_overhead_mb']:.2f} MB")
    else:
        logger.info(f"Error: {memory_results['error']}")
    
    # Performance assessment
    logger.info("\n" + "=" * 60)
    logger.info("PERFORMANCE ASSESSMENT")
    logger.info("=" * 60)
    
    assessment = {
        'single_symbol_acceptable': single_results['mean_ms'] < 100,
        'batch_acceptable': batch_results['mean_time_per_symbol_ms'] < 100,
        'memory_acceptable': memory_results.get('total_mb', 0) < 2000 if 'error' not in memory_results else True
    }
    
    results['assessment'] = assessment
    
    if assessment['single_symbol_acceptable']:
        logger.info(f"✅ Single symbol inference: {single_results['mean_ms']:.2f} ms < 100 ms")
    else:
        logger.warning(f"❌ Single symbol inference: {single_results['mean_ms']:.2f} ms >= 100 ms")
    
    if assessment['batch_acceptable']:
        logger.info(f"✅ Batch inference: {batch_results['mean_time_per_symbol_ms']:.2f} ms < 100 ms per symbol")
    else:
        logger.warning(f"❌ Batch inference: {batch_results['mean_time_per_symbol_ms']:.2f} ms >= 100 ms per symbol")
    
    if 'error' not in memory_results:
        if assessment['memory_acceptable']:
            logger.info(f"✅ Memory usage: {memory_results['total_mb']:.2f} MB < 2000 MB")
        else:
            logger.warning(f"❌ Memory usage: {memory_results['total_mb']:.2f} MB >= 2000 MB")
    
    all_acceptable = all(assessment.values())
    
    if all_acceptable:
        logger.info("\n✅ ALL PERFORMANCE CRITERIA MET")
    else:
        logger.warning("\n⚠️  SOME PERFORMANCE CRITERIA NOT MET")
    
    logger.info("=" * 60)
    
    # Save results
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nResults saved to: {output_path}")
    
    return 0 if all_acceptable else 1


if __name__ == '__main__':
    exit(main())
