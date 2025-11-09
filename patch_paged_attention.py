#!/usr/bin/env python3
"""
Fix vLLM CPU attention: add error handling and fallback for paged_attention_v1
"""
import os
import sys

def patch_paged_attention():
    """Add error handling for forward_decode in vLLM's cpu_attn.py"""
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
    if 'def _paged_attention_v1_fallback' in content:
        print(f'Patch already applied to {cpu_attn_path}')
        return True
    
    # Find code to replace (_PagedAttention.forward_decode)
    old_forward_decode = '''    @staticmethod
    def forward_decode(
        output: torch.Tensor,
        query: torch.Tensor,
        key_cache: torch.Tensor,
        value_cache: torch.Tensor,
        block_tables: torch.Tensor,
        context_lens: torch.Tensor,
        max_context_len: int,
        kv_cache_dtype: str,
        num_kv_heads: int,
        scale: float,
        alibi_slopes: torch.Tensor | None,
        k_scale: torch.Tensor,
        v_scale: torch.Tensor,
        *args,
    ) -> None:
        tp_rank: int = 0
        blocksparse_local_blocks: int = 0
        blocksparse_vert_stride: int = 0
        blocksparse_block_size: int = 64
        blocksparse_head_sliding_step: int = 0
        block_size = value_cache.shape[3]

        ops.paged_attention_v1(
            output,
            query,
            key_cache,
            value_cache,
            num_kv_heads,
            scale,
            block_tables,
            context_lens,
            block_size,
            max_context_len,
            alibi_slopes,
            kv_cache_dtype,
            k_scale,
            v_scale,
            tp_rank,
            blocksparse_local_blocks,
            blocksparse_vert_stride,
            blocksparse_block_size,
            blocksparse_head_sliding_step,
        )'''
    
    # New code (add error handling and PyTorch fallback)
    new_forward_decode = '''    @staticmethod
    def _paged_attention_v1_fallback(
        output: torch.Tensor,
        query: torch.Tensor,
        key_cache: torch.Tensor,
        value_cache: torch.Tensor,
        block_tables: torch.Tensor,
        context_lens: torch.Tensor,
        max_context_len: int,
        kv_cache_dtype: str,
        num_kv_heads: int,
        scale: float,
        alibi_slopes: torch.Tensor | None,
        k_scale: torch.Tensor,
        v_scale: torch.Tensor,
        block_size: int,
    ) -> None:
        """Fallback implementation using PyTorch native operations when paged_attention_v1 is unavailable"""
        # Simplified implementation: for each sequence, gather keys/values from cache and compute attention
        batch_size = query.shape[0]
        num_heads = query.shape[1]
        head_size = query.shape[2]
        
        # Initialize output
        output.zero_()
        
        for batch_idx in range(batch_size):
            seq_len = context_lens[batch_idx].item()
            if seq_len == 0:
                continue
            
            # Get block table for this sequence
            block_table = block_tables[batch_idx]  # [num_blocks]
            num_blocks = (seq_len + block_size - 1) // block_size
            
            # Gather keys and values from cache
            # key_cache: [num_blocks_total, num_kv_heads, head_size // x, block_size, x]
            # value_cache: [num_blocks_total, num_kv_heads, head_size, block_size]
            keys_list = []
            values_list = []
            
            for block_idx in range(min(num_blocks, len(block_table))):
                block_id = block_table[block_idx].item()
                if block_id < 0:
                    break
                
                # Extract keys and values from this block
                # Handle 5D key_cache
                if len(key_cache.shape) == 5:
                    # key_cache: [num_blocks, num_kv_heads, head_size // x, block_size, x]
                    x = key_cache.shape[4]
                    key_block = key_cache[block_id]  # [num_kv_heads, head_size // x, block_size, x]
                    key_block = key_block.view(num_kv_heads, head_size, block_size)  # Reshape to [num_kv_heads, head_size, block_size]
                else:
                    key_block = key_cache[block_id]  # [num_kv_heads, head_size, block_size]
                
                value_block = value_cache[block_id]  # [num_kv_heads, head_size, block_size]
                
                keys_list.append(key_block.transpose(1, 2))  # [num_kv_heads, block_size, head_size]
                values_list.append(value_block.transpose(1, 2))  # [num_kv_heads, block_size, head_size]
            
            if not keys_list:
                continue
            
            # Concatenate keys and values
            keys = torch.cat(keys_list, dim=1)  # [num_kv_heads, seq_len, head_size]
            values = torch.cat(values_list, dim=1)  # [num_kv_heads, seq_len, head_size]
            
            # Truncate to actual sequence length
            keys = keys[:, :seq_len, :]  # [num_kv_heads, seq_len, head_size]
            values = values[:, :seq_len, :]  # [num_kv_heads, seq_len, head_size]
            
            # Get query for this batch
            q = query[batch_idx]  # [num_heads, head_size]
            
            # Compute attention scores: Q @ K^T
            # q: [num_heads, head_size], keys: [num_kv_heads, seq_len, head_size]
            # We need to handle GQA (grouped query attention) where num_heads != num_kv_heads
            if num_heads == num_kv_heads:
                # Standard multi-head attention
                # q: [num_heads, head_size], keys: [num_kv_heads, seq_len, head_size]
                # For each head, compute q @ k^T
                # q: [num_heads, 1, head_size], keys: [num_kv_heads, head_size, seq_len]
                q_expanded = q.unsqueeze(1)  # [num_heads, 1, head_size]
                keys_t = keys.transpose(1, 2)  # [num_kv_heads, head_size, seq_len]
                scores = torch.bmm(q_expanded, keys_t)  # [num_heads, 1, seq_len]
                scores = scores * scale
                attn_weights = torch.softmax(scores, dim=-1)  # [num_heads, 1, seq_len]
                attn_output = torch.bmm(attn_weights, values)  # [num_heads, 1, head_size]
                output[batch_idx] = attn_output.squeeze(1)  # [num_heads, head_size]
            else:
                # GQA: repeat keys/values for each query head
                num_q_per_kv = num_heads // num_kv_heads
                keys_expanded = keys.repeat_interleave(num_q_per_kv, dim=0)  # [num_heads, seq_len, head_size]
                values_expanded = values.repeat_interleave(num_q_per_kv, dim=0)  # [num_heads, seq_len, head_size]
                
                q_expanded = q.unsqueeze(1)  # [num_heads, 1, head_size]
                keys_t = keys_expanded.transpose(1, 2)  # [num_heads, head_size, seq_len]
                scores = torch.bmm(q_expanded, keys_t)  # [num_heads, 1, seq_len]
                scores = scores * scale
                attn_weights = torch.softmax(scores, dim=-1)  # [num_heads, 1, seq_len]
                attn_output = torch.bmm(attn_weights, values_expanded)  # [num_heads, 1, head_size]
                output[batch_idx] = attn_output.squeeze(1)  # [num_heads, head_size]
    
    @staticmethod
    def forward_decode(
        output: torch.Tensor,
        query: torch.Tensor,
        key_cache: torch.Tensor,
        value_cache: torch.Tensor,
        block_tables: torch.Tensor,
        context_lens: torch.Tensor,
        max_context_len: int,
        kv_cache_dtype: str,
        num_kv_heads: int,
        scale: float,
        alibi_slopes: torch.Tensor | None,
        k_scale: torch.Tensor,
        v_scale: torch.Tensor,
        *args,
    ) -> None:
        tp_rank: int = 0
        blocksparse_local_blocks: int = 0
        blocksparse_vert_stride: int = 0
        blocksparse_block_size: int = 64
        blocksparse_head_sliding_step: int = 0
        block_size = value_cache.shape[3]
        
        try:
            ops.paged_attention_v1(
                output,
                query,
                key_cache,
                value_cache,
                num_kv_heads,
                scale,
                block_tables,
                context_lens,
                block_size,
                max_context_len,
                alibi_slopes,
                kv_cache_dtype,
                k_scale,
                v_scale,
                tp_rank,
                blocksparse_local_blocks,
                blocksparse_vert_stride,
                blocksparse_block_size,
                blocksparse_head_sliding_step,
            )
        except (AttributeError, RuntimeError) as e:
            # Use PyTorch fallback implementation
            try:
                _PagedAttention._paged_attention_v1_fallback(
                    output, query, key_cache, value_cache,
                    block_tables, context_lens, max_context_len,
                    kv_cache_dtype, num_kv_heads, scale, alibi_slopes,
                    k_scale, v_scale, block_size
                )
            except Exception as e2:
                raise RuntimeError(
                    f"vLLM CPU paged_attention_v1 operations are not available and fallback failed. "
                    f"Original error: {e}, fallback error: {e2}. "
                    f"Please ensure vLLM was built with CPU support or use IPEX."
                ) from e2'''
    
    # Replace
    if old_forward_decode in content:
        content = content.replace(old_forward_decode, new_forward_decode)
    else:
        print(f'Warning: Target code not found in {cpu_attn_path}')
        # Try more flexible matching
        import re
        pattern = r'(@staticmethod\s+def forward_decode\([^)]+\):\s+block_size = value_cache\.shape\[3\]\s+ops\.paged_attention_v1\([^)]+\))'
        match = re.search(pattern, content, re.DOTALL)
        if match:
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
    success = patch_paged_attention()
    sys.exit(0 if success else 1)

