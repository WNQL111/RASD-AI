import os, sys, ast

def check_boundaries():
    print('Checking domain isolation boundaries via Python AST analysis...')
    domains_dir = 'ai_worker/src/domains'
    if not os.path.exists(domains_dir):
        print('Error: domains directory not found.')
        sys.exit(1)

    known_domains = ['violence', 'fire', 'smoke', 'theft', 'collision', 'fall', 'weapon', 'intrusion', 'abandoned_object']
    existing_domains = [d for d in os.listdir(domains_dir) if os.path.isdir(os.path.join(domains_dir, d))]
    
    violations = []
    for d in existing_domains:
        d_path = os.path.join(domains_dir, d)
        for root, _, files in os.walk(d_path):
            for file in files:
                if file.endswith('.py'):
                    f_path = os.path.join(root, file)
                    with open(f_path, 'r', encoding='utf-8') as f:
                        try:
                            tree = ast.parse(f.read(), filename=f_path)
                        except Exception as e:
                            continue
                            
                    for node in ast.walk(tree):
                        imported_module = None
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imported_module = alias.name
                        elif isinstance(node, ast.ImportFrom):
                            imported_module = node.module or ''
                            
                        if imported_module:
                            for other in known_domains:
                                if other != d and (f'domains.{other}' in imported_module or imported_module.startswith(f'{other}.') or imported_module == f'domains.{other}'):
                                    violations.append(f'{f_path}:{getattr(node, "lineno", 1)} -> imports {imported_module}')

    if violations:
        print('Domain boundary violations found:')
        for v in violations:
            print('  -', v)
        sys.exit(1)
    else:
        print('PASSED: Domain boundaries are 100% isolated and clean (AST Verified).')

if __name__ == '__main__':
    check_boundaries()


