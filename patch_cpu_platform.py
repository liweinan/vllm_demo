#!/usr/bin/env python3
"""
Fix vLLM CPU platform detection: add check for VLLM_TARGET_DEVICE environment variable
"""
import os
import sys

def patch_vllm_platforms():
    """Add VLLM_TARGET_DEVICE check in vLLM's platforms/__init__.py"""
    # Find vllm.platforms.__init__.py file
    vllm_platforms_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', 'platforms', '__init__.py')
        if os.path.exists(test_path):
            vllm_platforms_path = test_path
            break
    
    if not vllm_platforms_path:
        print('Warning: vllm.platforms.__init__.py not found')
        return False
    
    # Read file content
    with open(vllm_platforms_path, 'r') as f:
        content = f.read()
    
    # Check if patch already applied
    if 'VLLM_TARGET_DEVICE' in content and 'Confirmed CPU platform is available because VLLM_TARGET_DEVICE=cpu' in content:
        print(f'Patch already applied to {vllm_platforms_path}')
        return True
    
    # Find code to replace
    old_check = 'is_cpu = vllm_version_matches_substr("cpu")'
    if old_check not in content:
        print(f'Warning: Target code not found in {vllm_platforms_path}')
        return False
    
    # New code (add VLLM_TARGET_DEVICE check)
    new_check = '''# Check if VLLM_TARGET_DEVICE is set to cpu
        import os
        vllm_target_device = os.getenv("VLLM_TARGET_DEVICE", "").lower()
        if vllm_target_device == "cpu":
            is_cpu = True
            logger.debug(
                "Confirmed CPU platform is available because VLLM_TARGET_DEVICE=cpu."
            )
        
        if not is_cpu:
            is_cpu = vllm_version_matches_substr("cpu")'''
    
    # Replace
    content = content.replace(old_check, new_check)
    
    # Write back to file
    with open(vllm_platforms_path, 'w') as f:
        f.write(content)
    
    print(f'Successfully patched {vllm_platforms_path}')
    return True

if __name__ == '__main__':
    success = patch_vllm_platforms()
    sys.exit(0 if success else 1)

