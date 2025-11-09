#!/usr/bin/env python3
"""
Fix vLLM _custom_ops: add error handling and fallback for reshape_and_cache
"""
import os
import sys

def patch_custom_ops():
    """Add error handling for reshape_and_cache in vLLM's _custom_ops.py"""
    # Find vllm._custom_ops file
    custom_ops_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', '_custom_ops.py')
        if os.path.exists(test_path):
            custom_ops_path = test_path
            break
    
    if not custom_ops_path:
        print('Warning: vllm._custom_ops.py not found')
        return False
    
    # Read file content
    with open(custom_ops_path, 'r') as f:
        content = f.read()
    
    # Check if patch already applied (check new logic)
    if 'cache_ops_candidates' in content and 'getattr(cache_ops, \'reshape_and_cache\', None)' in content:
        print(f'Patch already applied to {custom_ops_path}')
        return True
    
    # Find code to replace (could be original version or old patch version)
    # First try to match old patch version
    old_reshape_and_cache_v1 = '''def reshape_and_cache(
    key: torch.Tensor,
    value: torch.Tensor,
    key_cache: torch.Tensor,
    value_cache: torch.Tensor,
    slot_mapping: torch.Tensor,
    kv_cache_dtype: str,
    k_scale: torch.Tensor,
    v_scale: torch.Tensor,
) -> None:
    # Try different possible namespaces for cache ops
    cache_ops_namespaces = [
        torch.ops._C_cache_ops,
        getattr(torch.ops, 'vllm_cache_ops', None),
        getattr(torch.ops, 'vllm_C_cache_ops', None),
    ]
    
    last_error = None
    for cache_ops in cache_ops_namespaces:
        if cache_ops is None:
            continue
        try:
            cache_ops.reshape_and_cache(
                key,
                value,
                key_cache,
                value_cache,
                slot_mapping,
                kv_cache_dtype,
                k_scale,
                v_scale,
            )
            return
        except (AttributeError, RuntimeError) as e:
            last_error = e
            continue
    
    # If all attempts failed, raise error
    logger.error(
        f"Failed to use reshape_and_cache: {last_error}. "
        "vLLM CPU cache operations are not available. "
        "This may indicate that vLLM CPU cache ops were not properly compiled. "
        "Please ensure vLLM was built with CPU support, or use IPEX."
    )
    raise RuntimeError(
        "vLLM CPU cache operations are not available. "
        "Please rebuild vLLM with CPU support or use IPEX."
    ) from last_error'''
    
    # Original version (if old patch doesn't exist)
    old_reshape_and_cache_v0 = '''def reshape_and_cache(
    key: torch.Tensor,
    value: torch.Tensor,
    key_cache: torch.Tensor,
    value_cache: torch.Tensor,
    slot_mapping: torch.Tensor,
    kv_cache_dtype: str,
    k_scale: torch.Tensor,
    v_scale: torch.Tensor,
) -> None:
    torch.ops._C_cache_ops.reshape_and_cache(
        key,
        value,
        key_cache,
        value_cache,
        slot_mapping,
        kv_cache_dtype,
        k_scale,
        v_scale,
    )'''
    
    # New code (add error handling, try different namespaces)
    # Note: don't use logger, directly raise, avoid import issues
    new_reshape_and_cache = '''def reshape_and_cache(
    key: torch.Tensor,
    value: torch.Tensor,
    key_cache: torch.Tensor,
    value_cache: torch.Tensor,
    slot_mapping: torch.Tensor,
    kv_cache_dtype: str,
    k_scale: torch.Tensor,
    v_scale: torch.Tensor,
) -> None:
    # Try different possible namespaces for cache ops
    cache_ops_candidates = [
        ('_C_cache_ops', lambda: getattr(torch.ops, '_C_cache_ops', None)),
        ('vllm_cache_ops', lambda: getattr(torch.ops, 'vllm_cache_ops', None)),
        ('vllm_C_cache_ops', lambda: getattr(torch.ops, 'vllm_C_cache_ops', None)),
    ]
    
    last_error = None
    for name, get_cache_ops in cache_ops_candidates:
        try:
            cache_ops = get_cache_ops()
            if cache_ops is None:
                continue
            # Try to get reshape_and_cache method
            reshape_func = getattr(cache_ops, 'reshape_and_cache', None)
            if reshape_func is None:
                continue
            # Call the function
            reshape_func(
                key,
                value,
                key_cache,
                value_cache,
                slot_mapping,
                kv_cache_dtype,
                k_scale,
                v_scale,
            )
            return
        except (AttributeError, RuntimeError, TypeError) as e:
            last_error = e
            continue
    
    # If all attempts failed, raise error (don't use logger to avoid import issues)
    raise RuntimeError(
        f"vLLM CPU cache operations are not available. "
        f"Failed to use reshape_and_cache. Last error: {last_error}. "
        f"This may indicate that vLLM CPU cache ops were not properly compiled. "
        f"Please ensure vLLM was built with CPU support, or use IPEX."
    ) from last_error'''
    
    # Replace (first try old patch version, then original version)
    if old_reshape_and_cache_v1 in content:
        content = content.replace(old_reshape_and_cache_v1, new_reshape_and_cache)
        print(f'Replaced old patch version in {custom_ops_path}')
    elif old_reshape_and_cache_v0 in content:
        content = content.replace(old_reshape_and_cache_v0, new_reshape_and_cache)
        print(f'Replaced original version in {custom_ops_path}')
    else:
        print(f'Warning: Target code not found in {custom_ops_path}')
        print('Trying to find reshape_and_cache function...')
        # Try using regex or more flexible matching
        import re
        pattern = r'def reshape_and_cache\([^)]+\):\s+.*?torch\.ops\._C_cache_ops\.reshape_and_cache'
        if re.search(pattern, content, re.DOTALL):
            # Found match, but need more precise replacement
            print('Found reshape_and_cache but pattern matching failed. Manual fix needed.')
            return False
        else:
            print('Could not find reshape_and_cache function to patch.')
            return False

    # Write back to file
    with open(custom_ops_path, 'w') as f:
        f.write(content)
    
    print(f'Successfully patched {custom_ops_path}')
    return True

if __name__ == '__main__':
    success = patch_custom_ops()
    sys.exit(0 if success else 1)

