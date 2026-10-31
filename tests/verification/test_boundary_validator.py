import unittest, os, subprocess, shutil

class TestBoundaryValidatorAdversarial(unittest.TestCase):
    def test_validator_fails_on_illegal_import(self):
        # Create temporary illegal import file in domains/violence/
        temp_file = 'ai_worker/src/domains/violence/temp_illegal.py'
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write('from domains.fire import detector\n')
            
        try:
            res = subprocess.run(['python', 'tools/check_domain_boundaries.py'], capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, 'Boundary validator MUST fail on illegal cross-domain import.')
            self.assertIn('Domain boundary violations found', res.stdout)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_validator_passes_on_clean_state(self):
        res = subprocess.run(['python', 'tools/check_domain_boundaries.py'], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, 'Boundary validator MUST pass on clean architecture.')

if __name__ == '__main__':
    unittest.main()
