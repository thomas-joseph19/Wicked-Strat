import os

modules = [
    'data_loader.py', 
    'session.py', 
    'core.py', 
    'volume_profile.py', 
    'lvn.py', 
    'single_prints.py', 
    'tpo.py', 
    'swings.py', 
    'ismt.py', 
    'smt.py', 
    'entry.py', 
    'position.py', 
    'metrics.py', 
    'plotting.py', 
    'backtest.py', 
    'utils.py', 
    'ml_pipeline.py'
]

os.makedirs('src', exist_ok=True)

for m in modules:
    path = os.path.join('src', m)
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write(f'# Stub for {m}\n\n')
            f.write('def stub_func():\n')
            f.write('    raise NotImplementedError("This module is a placeholder for future phases")\n')

print(f"Created {len(modules)} stubs in src/")
