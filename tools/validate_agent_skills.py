import os, sys

def validate_skills():
    print('Validating Agent Skills Factory schemas across 16 domain groups...')
    skills_dir = '.agents/skills'
    if not os.path.exists(skills_dir):
        print('Error: .agents/skills directory not found.')
        sys.exit(1)

    subdirs = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]
    missing_skills = []
    invalid_skills = []
    
    for sd in subdirs:
        skill_file = os.path.join(skills_dir, sd, 'SKILL.md')
        if not os.path.exists(skill_file):
            missing_skills.append(sd)
            continue
            
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'name:' not in content or 'description:' not in content:
                invalid_skills.append(sd)

    if missing_skills or invalid_skills:
        print(f'Skill validation failed. Missing: {missing_skills}, Invalid: {invalid_skills}')
        sys.exit(1)

    print(f'PASSED: All {len(subdirs)} Agent Skill schemas are valid and complete.')

if __name__ == '__main__':
    validate_skills()

