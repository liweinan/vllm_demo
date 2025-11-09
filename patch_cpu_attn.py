#!/usr/bin/env python3
"""
Fix vLLM CPU attention backend: add error handling and fallback for reshape_and_cache
"""
import os
import sys

def patch_cpu_attn():
    """Add error handling for write_to_paged_cache in vLLM's cpu_attn.py"""
    # Find vllm.v1.attention.backends.cpu_attn file
    cpu_attn_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', 'v1', 'attention', 'backends', 'cpu_attn.py')
        if os.path.exists(test_path):
            cpu_attn_path = test_path
            break
    
    if not cpu_attn_path:
        print('Warning: vllm.v1.attention.backends.cpu_attn.py not found')
        return False
    
    # Read file content
    with open(cpu_attn_path, 'r') as f:
        content = f.read()
    
    # Check if patch already applied
    if 'def _reshape_and_cache_fallback' in content:
        print(f'Patch already applied to {cpu_attn_path}')
        return True
    
    # Find code to replace
    old_write_to_paged_cache = '''    @staticmethod
    def write_to_paged_cache(
        key: torch.Tensor,
        value: torch.Tensor,
        key_cache: torch.Tensor,
        value_cache: torch.Tensor,
        slot_mapping: torch.Tensor,
        kv_cache_dtype: str,
        k_scale: torch.Tensor,
        v_scale: torch.Tensor,
        *args,
    ) -> None:
        ops.reshape_and_cache(
            key,
            value,
            key_cache,
            value_cache,
            slot_mapping.flatten(),
            kv_cache_dtype,
            k_scale,
            v_scale,
        )'''
    
    # New code (add error handling and PyTorch fallback)
    new_write_to_paged_cache = '''    @staticmethod
    def _reshape_and_cache_fallback(
        key: torch.Tensor,
        value: torch.Tensor,
        key_cache: torch.Tensor,
        value_cache: torch.Tensor,
        slot_mapping: torch.Tensor,
        kv_cache_dtype: str,
        k_scale: torch.Tensor,
        v_scale: torch.Tensor,
    ) -> None:
        """Fallback implementation using PyTorch native operations when cache ops are unavailable"""
        # slot_mapping: [num_tokens] - absolute slot indices
        num_tokens = key.shape[0]
        num_kv_heads = key.shape[1]
        head_size = key.shape[2]
        
        # Get cache shapes from split_kv_cache output
        # key_cache: [num_blocks, num_kv_heads, head_size // x, block_size, x] (5D)
        # value_cache: [num_blocks, num_kv_heads, head_size, block_size] (4D)
        num_blocks = key_cache.shape[0]
        if len(key_cache.shape) == 5:
            # key_cache is 5D: [num_blocks, num_kv_heads, head_size // x, block_size, x]
            block_size = key_cache.shape[3]
            x = key_cache.shape[4]  # Usually 16 // element_size
        else:
            # Fallback: assume 4D
            block_size = key_cache.shape[-1]
            x = 1
        
        # Flatten slot_mapping
        slot_mapping_flat = slot_mapping.flatten()  # [num_tokens]
        
        # Calculate block and slot indices for each token
        block_indices = slot_mapping_flat // block_size  # [num_tokens]
        slot_indices = slot_mapping_flat % block_size    # [num_tokens]
        
        # For each KV head, write tokens to cache
        # key: [num_tokens, num_kv_heads, head_size]
        # value: [num_tokens, num_kv_heads, head_size]
        for head_idx in range(num_kv_heads):
            for token_idx in range(num_tokens):
                block_idx = block_indices[token_idx].item()
                slot_idx = slot_indices[token_idx].item()
                
                # Handle key_cache: 5D shape [num_blocks, num_kv_heads, head_size // x, block_size, x]
                if len(key_cache.shape) == 5:
                    # Reshape key slice to match cache format
                    key_slice = key[token_idx, head_idx, :]  # [head_size]
                    key_slice_reshaped = key_slice.view(head_size // x, x)  # [head_size // x, x]
                    key_cache[block_idx, head_idx, :, slot_idx, :] = key_slice_reshaped
                else:
                    # Fallback for 4D
                    key_cache[block_idx, head_idx, :, slot_idx] = key[token_idx, head_idx, :]
                
                # value_cache: 4D shape [num_blocks, num_kv_heads, head_size, block_size]
                value_cache[block_idx, head_idx, :, slot_idx] = value[token_idx, head_idx, :]
    
    @staticmethod
    def write_to_paged_cache(
        key: torch.Tensor,
        value: torch.Tensor,
        key_cache: torch.Tensor,
        value_cache: torch.Tensor,
        slot_mapping: torch.Tensor,
        kv_cache_dtype: str,
        k_scale: torch.Tensor,
        v_scale: torch.Tensor,
        *args,
    ) -> None:
        try:
            ops.reshape_and_cache(
                key,
                value,
                key_cache,
                value_cache,
                slot_mapping.flatten(),
                kv_cache_dtype,
                k_scale,
                v_scale,
            )
        except (AttributeError, RuntimeError) as e:
            # Try to import cache ops directly
            try:
                import vllm._C_cache_ops  # noqa: F401
                # Retry after importing
                ops.reshape_and_cache(
                    key,
                    value,
                    key_cache,
                    value_cache,
                    slot_mapping.flatten(),
                    kv_cache_dtype,
                    k_scale,
                    v_scale,
                )
            except (ImportError, AttributeError, RuntimeError) as e2:
                # Use PyTorch fallback implementation
                try:
                    _PagedAttention._reshape_and_cache_fallback(
                        key, value, key_cache, value_cache,
                        slot_mapping.flatten(), kv_cache_dtype, k_scale, v_scale
                    )
                except Exception as e3:
                    raise RuntimeError(
                        f"vLLM CPU cache operations are not available and fallback failed. "
                        f"Original error: {e}, import error: {e2}, fallback error: {e3}. "
                        f"Please ensure vLLM was built with CPU support or use IPEX."
                    ) from e3'''
    
    # Replace
    if old_write_to_paged_cache in content:
        content = content.replace(old_write_to_paged_cache, new_write_to_paged_cache)
    else:
        print(f'Warning: Target code not found in {cpu_attn_path}')
        # Try more flexible matching
        import re
        pattern = r'(@staticmethod\s+def write_to_paged_cache\([^)]+\):\s+ops\.reshape_and_cache\([^)]+\))'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            # More complex replacement logic
            print('Found pattern with regex, but manual replacement needed')
            return False
        else:
            return False
    
    # Write back to file
    with open(cpu_attn_path, 'w') as f:
        f.write(content)
    
    print(f'Successfully patched {cpu_attn_path}')
    return True

if __name__ == '__main__':
    success = patch_cpu_attn()
    sys.exit(0 if success else 1)

