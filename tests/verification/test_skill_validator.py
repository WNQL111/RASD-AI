import unittest, os, subprocess, shutil

class TestSkillValidatorAdversarial(unittest.TestCase):
    def test_validator_fails_on_invalid_skill(self):
        temp_skill_dir = '.agents/skills/temp_invalid_skill'
        os.makedirs(temp_skill_dir, exist_ok=True)
        bad_md = os.path.join(temp_skill_dir, 'SKILL.md')
        with open(bad_md, 'w', encoding='utf-8') as f:
            f.write('# Invalid Skill without YAML metadata\n')

        try:
            res = subprocess.run(['python', 'tools/validate_agent_skills.py'], capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, 'Skill validator MUST fail on invalid skill file.')
        finally:
            if os.path.exists(temp_skill_dir):
                shutil.rmtree(temp_skill_dir)

    def test_validator_passes_on_valid_skills(self):
        res = subprocess.run(['python', 'tools/validate_agent_skills.py'], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, 'Skill validator MUST pass on clean skills.')

if __name__ == '__main__':
    unittest.main()
