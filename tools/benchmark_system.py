import sys, os
from benchmark_crowd_behavior import run_benchmark

if __name__ == '__main__':
    v_path = sys.argv[1] if len(sys.argv) > 1 else r'E:\final project\mall waking.mp4'
    run_benchmark(v_path)
