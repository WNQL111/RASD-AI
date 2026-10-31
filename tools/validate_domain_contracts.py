import os, sys, importlib

def validate_contracts():
    print('Validating domain contracts and exported DTO schemas...')
    required_files = ['__init__.py', 'config.py', 'models.py', 'evidence.py', 'temporal.py', 'decision.py', 'detector.py']
    domains_dir = 'ai_worker/src/domains'
    domains = [d for d in os.listdir(domains_dir) if os.path.isdir(os.path.join(domains_dir, d))]
    
    missing = []
    for d in domains:
        d_path = os.path.join(domains_dir, d)
        for req in required_files:
            if not os.path.exists(os.path.join(d_path, req)):
                missing.append(f'{d}/{req}')
                
    if missing:
        print('Domain contract validation errors:')
        for m in missing:
            print('  - Missing file:', m)
        sys.exit(1)

    # Inspect Violence Domain exports specifically
    try:
        sys.path.insert(0, os.path.abspath('ai_worker/src'))
        v_module = importlib.import_module('domains.violence')
        required_v_exports = ['ViolenceDomainDetector', 'ViolenceDomainConfig', 'ViolenceEvidence', 'ViolenceDecision']
        for exp in required_v_exports:
            if not hasattr(v_module, exp):
                print(f'Error: Missing expected export {exp} in domains.violence')
                sys.exit(1)

        c_module = importlib.import_module('domains.collision')
        required_c_exports = ['CollisionDomainDetector', 'CollisionConfig', 'CollisionEvidenceDTO', 'CollisionDecisionDTO']
        for exp in required_c_exports:
            if not hasattr(c_module, exp):
                print(f'Error: Missing expected export {exp} in domains.collision')
                sys.exit(1)

        print('PASSED: All domain contracts and exported DTO schemas are verified.')
    except Exception as e:
        print('Domain contract validation error:', e)
        sys.exit(1)

if __name__ == '__main__':
    validate_contracts()

