import sys
import os
import time
import unittest
import asyncio

# Ensure sys.path contains ai_worker/src and backend/app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app"))

from core.event_schema import EventEnvelope, EventTypes
from services.event_processor import EventProcessor, event_processor
from services.broadcaster import BroadcasterManager

class TestE2ERealtimeIntegration(unittest.TestCase):
    def setUp(self):
        self.processor = EventProcessor(max_history_capacity=50)
        self.broadcaster = BroadcasterManager(history_limit=50)

    # 1. Event Envelope Schema Validation
    def test_01_event_envelope_contract_schema(self):
        envelope = EventEnvelope(
            event_id="evt_1001",
            trace_id="tr_1001",
            type=EventTypes.VIOLENCE_CONFIRMED,
            camera_id="cam_1",
            sequence=1,
            severity="CRITICAL",
            confidence=0.95,
            risk_score=0.88,
            escalation_stage="CONFIRMED",
            participants=[1, 2],
            reason_codes=["RAPID_APPROACH", "HEADON_TRAJECTORY"]
        )
        payload = envelope.to_dict()

        self.assertEqual(payload["event_id"], "evt_1001")
        self.assertEqual(payload["type"], EventTypes.VIOLENCE_CONFIRMED)
        self.assertEqual(payload["event_version"], "1.0")
        self.assertTrue(self.processor.validate_schema(payload))

    # 2. Idempotency & Deduplication Test
    def test_02_idempotency_and_deduplication(self):
        envelope = EventEnvelope(event_id="evt_unique_100", type=EventTypes.VIOLENCE_CANDIDATE)
        payload = envelope.to_dict()

        p1 = self.processor.process_incoming_event(payload)
        self.assertIsNotNone(p1)

        # Duplicate delivery of exact same event_id
        p2 = self.processor.process_incoming_event(payload)
        self.assertIsNone(p2) # Deduplicated & ignored!

    # 3. Sequence Ordering Tracking
    def test_03_sequence_ordering(self):
        e1 = EventEnvelope(event_id="e1", camera_id="cam_A", sequence=1).to_dict()
        e2 = EventEnvelope(event_id="e2", camera_id="cam_A", sequence=2).to_dict()

        self.processor.process_incoming_event(e1)
        self.assertEqual(self.processor.last_sequence_by_camera.get("cam_A"), 1)

        self.processor.process_incoming_event(e2)
        self.assertEqual(self.processor.last_sequence_by_camera.get("cam_A"), 2)

    # 4. SSE Broadcaster & Last-Event-ID Resync Replay
    def test_04_sse_last_event_id_resync(self):
        async def run_async_test():
            e1 = {"event_id": "evt_r1", "type": "alert", "msg": "Event 1"}
            e2 = {"event_id": "evt_r2", "type": "alert", "msg": "Event 2"}
            e3 = {"event_id": "evt_r3", "type": "alert", "msg": "Event 3"}

            await self.broadcaster.broadcast(e1)
            await self.broadcaster.broadcast(e2)
            await self.broadcaster.broadcast(e3)

            # Reconnect with Last-Event-ID = evt_r1 (Expects e2, e3)
            missed = await self.broadcaster.get_events_since("evt_r1")
            self.assertEqual(len(missed), 2)
            self.assertEqual(missed[0]["event_id"], "evt_r2")
            self.assertEqual(missed[1]["event_id"], "evt_r3")

        asyncio.run(run_async_test())

if __name__ == "__main__":
    unittest.main()
