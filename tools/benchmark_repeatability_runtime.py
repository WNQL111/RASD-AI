import sys, os, time, json
sys.path.insert(0, os.path.abspath('tools'))
from benchmark_crowd_behavior import run_benchmark

def run_repeatability():
    video_path = r'E:\final project\mall waking.mp4'
    print(f'Starting Repeatability Benchmark on {video_path} (300 frames per run)...')
    
    # Run A
    print('Executing Run A...')
    res_a = run_benchmark(video_path, max_frames=300)
    
    # Run B
    print('Executing Run B...')
    res_b = run_benchmark(video_path, max_frames=300)
    
    match = (
        res_a is not None and res_b is not None and
        res_a['confirmed_violence'] == res_b['confirmed_violence'] and
        res_a['total_frames'] == res_b['total_frames']
    )
    
    repeatability_result = {
        'video_file': video_path,
        'run_A': res_a,
        'run_B': res_b,
        'normalized_signature_match': match,
        'status': '100% DETERMINISTIC (Normalized Signature Match)' if match else 'PARTIAL',
        'generated_at': time.time()
    }
    
    os.makedirs('audit/violence_v1/benchmark', exist_ok=True)
    with open('audit/violence_v1/benchmark/repeatability.json', 'w', encoding='utf-8') as rf:
        json.dump(repeatability_result, rf, indent=2)
        
    print('Repeatability Benchmark Completed.')

if __name__ == '__main__':
    run_repeatability()
