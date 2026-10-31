import sys, os, time, json
sys.path.insert(0, os.path.abspath('ai_worker/src'))
from domains.violence.temporal import ViolenceTemporalTracker

def run_temporal_test():
    print('Executing Real Temporal Memory & TTL Cleanup Test...')
    tracker = ViolenceTemporalTracker(duration_thresh=15, max_ttl_seconds=0.05)
    
    t0 = time.perf_counter()
    for i in range(10000):
        tracker.update_pair((i, i + 10000), active=False)
    t_pop = (time.perf_counter() - t0) * 1000.0
    
    state_before = len(tracker.state_acc)
    time.sleep(0.06)
    
    t1 = time.perf_counter()
    tracker.cleanup_expired_keys(time.time())
    t_clean = (time.perf_counter() - t1) * 1000.0
    state_after = len(tracker.state_acc)

    print(f'Populated 10,000 inactive pairs in {t_pop:.2f}ms | State before: {state_before}')
    print(f'Cleaned up expired TTL keys in {t_clean:.2f}ms | State after: {state_after}')
    
    os.makedirs('audit/violence_v1/tests', exist_ok=True)
    out_file = 'audit/violence_v1/tests/temporal_cleanup_runtime.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            'provenance': 'tools/test_violence_temporal_runtime.py',
            'generated_at': time.time(),
            'keys_tested': 10000,
            'populate_latency_ms': round(t_pop, 2),
            'cleanup_latency_ms': round(t_clean, 2),
            'state_size_before': state_before,
            'state_size_after': state_after,
            'memory_leak_status': 'ZERO_LEAK_CONFIRMED' if state_after == 0 else 'LEAK_DETECTED'
        }, f, indent=2)
    print(f'Saved temporal runtime results to {out_file}')

if __name__ == '__main__':
    run_temporal_test()
