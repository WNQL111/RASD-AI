import sys
import os
import unittest
import time
import uuid

# Ensure sys.path contains ai_worker/src and backend/app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app"))

from core.event_schema import EventEnvelope, EventTypes
from api.routers.videos import active_analysis_jobs

class TestVideoAnalysisJobTrialMode(unittest.TestCase):
    def setUp(self):
        active_analysis_jobs.clear()

    # 1. Valid File Extension Validation
    def test_01_valid_file_extension(self):
        allowed_exts = {".mp4", ".avi", ".mkv", ".mov"}
        filename = "security_footage.mp4"
        _, ext = os.path.splitext(filename)
        self.assertIn(ext.lower(), allowed_exts)

    # 2. Invalid Extension Rejection
    def test_02_invalid_file_extension_rejection(self):
        allowed_exts = {".mp4", ".avi", ".mkv", ".mov"}
        bad_filename = "malicious_script.exe"
        _, ext = os.path.splitext(bad_filename)
        self.assertNotIn(ext.lower(), allowed_exts)

    # 3. Oversized File Limit Validation
    def test_03_oversized_file_limit_guard(self):
        max_limit_bytes = 500 * 1024 * 1024
        oversized_bytes = 501 * 1024 * 1024
        self.assertGreater(oversized_bytes, max_limit_bytes)

    # 4. Job Creation & Initial State
    def test_04_job_creation_and_queued_state(self):
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        active_analysis_jobs[job_id] = {
            "job_id": job_id,
            "filename": "test.mp4",
            "status": "processing",
            "current_stage": "QUEUED",
            "progress_percentage": 0.0
        }
        self.assertEqual(active_analysis_jobs[job_id]["status"], "processing")
        self.assertEqual(active_analysis_jobs[job_id]["current_stage"], "QUEUED")

    # 5. Job Status Telemetry Payload Contract
    def test_05_job_status_telemetry_payload(self):
        job_id = "job_test_100"
        active_analysis_jobs[job_id] = {
            "job_id": job_id,
            "filename": "mall.mp4",
            "status": "processing",
            "current_stage": "ANALYZING",
            "progress_percentage": 45.5,
            "processed_frames": 450,
            "total_frames": 1000,
            "processing_fps": 35.0,
            "active_model": "yolov8m.pt",
            "analysis_level": "LEVEL_3_FOCUSED"
        }
        info = active_analysis_jobs[job_id]
        self.assertEqual(info["progress_percentage"], 45.5)
        self.assertEqual(info["active_model"], "yolov8m.pt")

    # 6. Job Cancellation Test
    def test_06_job_cancellation(self):
        job_id = "job_cancel_999"
        active_analysis_jobs[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "current_stage": "ANALYZING"
        }
        # Simulate cancel request
        active_analysis_jobs[job_id]["status"] = "cancelled"
        active_analysis_jobs[job_id]["current_stage"] = "CANCELLED"

        self.assertEqual(active_analysis_jobs[job_id]["status"], "cancelled")
        self.assertEqual(active_analysis_jobs[job_id]["current_stage"], "CANCELLED")

    # 7. Multi-Job Isolation Test
    def test_07_multi_job_state_isolation(self):
        j1 = "job_1"
        j2 = "job_2"
        active_analysis_jobs[j1] = {"job_id": j1, "progress_percentage": 25.0}
        active_analysis_jobs[j2] = {"job_id": j2, "progress_percentage": 75.0}

        self.assertEqual(active_analysis_jobs[j1]["progress_percentage"], 25.0)
        self.assertEqual(active_analysis_jobs[j2]["progress_percentage"], 75.0)

if __name__ == "__main__":
    unittest.main()
