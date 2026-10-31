import sys
import os
import time
import cv2
import json
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_worker', 'src')))

from detectors.yolo_detector import YoloDetector
from tracker.byte_tracker import ByteTracker
from core.pipeline import Pipeline
from core.device_manager import device_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('run_video_regression')

def run_video_regression(video_path: str = 'E:\\final project\\mall waking.mp4', max_frames: int = 300):
    if not os.path.exists(video_path):
        logger.error(f'Video file {video_path} not found!')
        return 1

    logger.info(f'Starting Video Regression Benchmark on {video_path}...')
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    detector = YoloDetector(model_dir='models', model_name='yolov8n.pt')
    tracker = ByteTracker(detector)
    pipeline = Pipeline(detector=detector)

    frame_idx = 0
    start_time = time.time()
    events_collected = []
    people_counts = []

    while True:
        if max_frames is not None and frame_idx >= max_frames:
            break
        ret, frame = cap.read()
        if not ret:
            break

        evs = pipeline.process_frame(frame, frame_idx, video_id=os.path.basename(video_path), tracker=tracker)
        if evs:
            events_collected.extend(evs)

        p_cnt = len([o for o in pipeline.memory.objects.values() if not o.lost_state and o.class_id == 0]) if hasattr(pipeline, 'memory') else 0
        people_counts.append(p_cnt)
        frame_idx += 1

    cap.release()
    total_time = time.time() - start_time
    effective_fps = round(frame_idx / total_time, 2) if total_time > 0 else 0.0
    realtime_ratio = round(effective_fps / video_fps, 2) if video_fps > 0 else 0.0

    mem_stats = device_manager.get_memory_stats()
    vram_mb = mem_stats.get('allocated_mb', 0.0)
    avg_people = round(sum(people_counts) / len(people_counts), 1) if people_counts else 0.0

    violence_events = [e for e in events_collected if 'violence' in str(e.get('type', ''))]
    collision_events = [e for e in events_collected if 'collision' in str(e.get('type', '')) or 'accident' in str(e.get('type', ''))]

    print('=' * 60)
    print('ASIS-V2 FULL MULTI-DOMAIN VIDEO REGRESSION REPORT')
    print('=' * 60)
    print(f'Video File           : {video_path}')
    print(f'Resolution           : {frame_w}x{frame_h}')
    print(f'Total Frames         : {frame_idx}')
    print(f'Processing Time      : {total_time:.2f} s')
    print(f'Effective FPS        : {effective_fps} FPS')
    print(f'Average People       : {avg_people}')
    print(f'VRAM Allocated       : {vram_mb:.1f} MB')
    print(f'Confirmed Violence   : {len(violence_events)}')
    print(f'Confirmed Collision  : {len(collision_events)}')
    print('=' * 60)

    summary = {
        'video_file': video_path,
        'resolution': f'{frame_w}x{frame_h}',
        'video_fps': round(video_fps, 2),
        'total_frames': frame_idx,
        'processing_seconds': round(total_time, 2),
        'effective_fps': effective_fps,
        'realtime_ratio': realtime_ratio,
        'people_avg': avg_people,
        'people_max': max(people_counts) if people_counts else 0,
        'confirmed_violence_events': len(violence_events),
        'confirmed_collision_events': len(collision_events),
        'gpu_vram_peak_mb': round(vram_mb, 1),
        'status': 'PASSED (0 False Violence Alarms, 0 False Collision Alarms)' if len(violence_events) == 0 and len(collision_events) == 0 else 'FAILED',
        'generated_at': time.time()
    }

    os.makedirs('audit/final_readiness', exist_ok=True)
    with open('audit/final_readiness/mall_regression.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print('Wrote audit/final_readiness/mall_regression.json')
    return 0

if __name__ == '__main__':
    v = sys.argv[1] if len(sys.argv) > 1 else 'E:\\final project\\mall waking.mp4'
    sys.exit(run_video_regression(v, max_frames=300))
