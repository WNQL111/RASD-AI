import unittest, os, subprocess

class TestContractValidatorAdversarial(unittest.TestCase):
    def test_validator_fails_on_missing_contract_file(self):
        temp_dir = 'ai_worker/src/domains/temp_broken_domain'
        os.makedirs(temp_dir, exist_ok=True)
        try:
            res = subprocess.run(['python', 'tools/validate_domain_contracts.py'], capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, 'Contract validator MUST fail when required contract file is missing.')
        finally:
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    def test_validator_passes_on_clean_contracts(self):
        res = subprocess.run(['python', 'tools/validate_domain_contracts.py'], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, 'Contract validator MUST pass on clean contracts.')

if __name__ == '__main__':
    unittest.main()
