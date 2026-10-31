import os
import sys
import json
import hashlib

def check_protected_domains():
    checksum_file = os.path.abspath('audit/protected_domains/VIOLENCE_V1_CHECKSUMS.json')
    if not os.path.exists(checksum_file):
        print(f'ERROR: Checksum ledger not found: {checksum_file}')
        return 1

    with open(checksum_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    mismatches = []
    missing = []
    verified = 0

    print('Verifying Protected Domain Baselines (SHA-256)...')

    for rel_path, expected_hash in baseline.items():
        full_path = os.path.abspath(rel_path)
        if not os.path.exists(full_path):
            missing.append(rel_path)
            continue

        with open(full_path, 'rb') as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()

        if current_hash != expected_hash:
            mismatches.append((rel_path, expected_hash, current_hash))
        else:
            verified += 1

    if missing:
        print(f'FAIL: {len(missing)} protected files are missing:')
        for p in missing:
            print(f'  - Missing: {p}')
        return 1

    if mismatches:
        print(f'FAIL: {len(mismatches)} protected files have been modified unexpectedly:')
        for p, exp, cur in mismatches:
            print(f'  - File: {p}')
            print(f'    Expected: {exp}')
            print(f'    Actual:   {cur}')
        return 1

    print(f'PASSED: All {verified} protected domain files match certified SHA-256 baselines (Zero Regression).')
    return 0

if __name__ == '__main__':
    sys.exit(check_protected_domains())
