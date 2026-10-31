import unittest
import torch
import sys
import os

# Add ai_worker/src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_worker', 'src')))

from core.device_manager import DeviceManager, device_manager

class TestDeviceManager(unittest.TestCase):
    """
    Unit and Fallback Tests for DeviceManager.
    """
    def test_singleton_instance(self):
        dm1 = DeviceManager()
        dm2 = DeviceManager()
        self.assertIs(dm1, dm2)
        self.assertIs(dm1, device_manager)

    def test_device_retrieval(self):
        dev = device_manager.get_device()
        self.assertIsInstance(dev, torch.device)
        self.assertIn(dev.type, ['cuda', 'mps', 'cpu'])

    def test_device_str(self):
        dev_str = device_manager.get_device_str()
        self.assertIsInstance(dev_str, str)
        self.assertTrue(len(dev_str) > 0)

    def test_memory_stats(self):
        stats = device_manager.get_memory_stats()
        self.assertIn('device', stats)
        self.assertIn('is_gpu', stats)
        self.assertIn('allocated_mb', stats)

if __name__ == '__main__':
    unittest.main()
