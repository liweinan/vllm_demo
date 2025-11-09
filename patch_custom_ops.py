#!/usr/bin/env python3
"""
修复 vLLM _custom_ops：为 reshape_and_cache 添加错误处理和 fallback
"""
import os
import sys

def patch_custom_ops():
    """在 vLLM 的 _custom_ops.py 中为 reshape_and_cache 添加错误处理"""
    # 查找 vllm._custom_ops 文件
    custom_ops_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', '_custom_ops.py')
        if os.path.exists(test_path):
            custom_ops_path = test_path
            break
    
    if not custom_ops_path:
        print('Warning: vllm._custom_ops.py not found')
        return False
    
    # 读取文件内容
    with open(custom_ops_path, 'r') as f:
        content = f.read()
    
    # 检查是否已经应用了补丁（检查新的逻辑）
    if 'cache_ops_candidates' in content and 'getattr(cache_ops, \'reshape_and_cache\', None)' in content:
        print(f'Patch already applied to {custom_ops_path}')
        return True
    
    # 查找要替换的代码（可能是原始版本或旧补丁版本）
    # 先尝试匹配旧补丁版本
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
    
    # 原始版本（如果旧补丁不存在）
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
    
    # 新的代码（添加错误处理，尝试不同的命名空间）
    # 注意：不使用 logger，直接 raise，避免导入问题
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
    
    # 替换（先尝试旧补丁版本，再尝试原始版本）
    if old_reshape_and_cache_v1 in content:
        content = content.replace(old_reshape_and_cache_v1, new_reshape_and_cache)
        print(f'Replaced old patch version in {custom_ops_path}')
    elif old_reshape_and_cache_v0 in content:
        content = content.replace(old_reshape_and_cache_v0, new_reshape_and_cache)
        print(f'Replaced original version in {custom_ops_path}')
    else:
        print(f'Warning: Target code not found in {custom_ops_path}')
        print('Trying to find reshape_and_cache function...')
        # 尝试使用正则表达式或更灵活的匹配
        import re
        pattern = r'def reshape_and_cache\([^)]+\):\s+.*?torch\.ops\._C_cache_ops\.reshape_and_cache'
        if re.search(pattern, content, re.DOTALL):
            # 找到匹配，但需要更精确的替换
            print('Found reshape_and_cache but pattern matching failed. Manual fix needed.')
            return False
        else:
            print('Could not find reshape_and_cache function to patch.')
            return False
    
    # 写回文件
    with open(custom_ops_path, 'w') as f:
        f.write(content)
    
    print(f'Successfully patched {custom_ops_path}')
    return True

if __name__ == '__main__':
    success = patch_custom_ops()
    sys.exit(0 if success else 1)

