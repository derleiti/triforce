#!/usr/bin/env python3
"""Verify dependency compatibility without installing"""

requirements = {
    'anthropic': {'httpx': '>=0.23.0,<1'},
    'openai': {'httpx': '>=0.23.0,<1'},
    'mistralai': {'httpx': '>=0.28.1'},
}

httpx_version = '0.28.1'

print("🔍 Dependency Compatibility Check")
print("=" * 50)
print(f"\nProposed httpx version: {httpx_version}")
print()

def check_constraint(version, constraint):
    """Simple version check"""
    v = tuple(map(int, version.split('.')))
    
    if '>=' in constraint and '<' in constraint:
        parts = constraint.split(',')
        lower = parts[0].replace('>=', '').strip()
        upper = parts[1].replace('<', '').strip()
        v_lower = tuple(map(int, lower.split('.')))
        v_upper = tuple(map(int, upper.split('.')))
        return v >= v_lower and v < v_upper
    elif '>=' in constraint:
        lower = constraint.replace('>=', '').strip()
        v_lower = tuple(map(int, lower.split('.')))
        return v >= v_lower
    elif '<' in constraint:
        upper = constraint.replace('<', '').strip()
        v_upper = tuple(map(int, upper.split('.')))
        return v < v_upper
    
    return True

all_ok = True
for package, deps in requirements.items():
    for dep, constraint in deps.items():
        compatible = check_constraint(httpx_version, constraint)
        status = '✅' if compatible else '❌'
        print(f"{status} {package:12} requires {dep} {constraint:20} → {httpx_version}")
        if not compatible:
            all_ok = False

print()
if all_ok:
    print("✅ ALL DEPENDENCIES COMPATIBLE!")
    print(f"   httpx=={httpx_version} satisfies all requirements")
else:
    print("❌ CONFLICTS DETECTED!")
    exit(1)
