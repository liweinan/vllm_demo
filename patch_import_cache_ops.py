#!/usr/bin/env python3
"""
修复 vLLM platforms：在 import_kernels 中添加 cache ops 导入
"""
import os
import sys

def patch_platforms_import_kernels():
    """在 vLLM 的 platforms/interface.py 中为 import_kernels 添加 cache ops 导入"""
    # 查找 vllm.platforms.interface 文件
    interface_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', 'platforms', 'interface.py')
        if os.path.exists(test_path):
            interface_path = test_path
            break
    
    if not interface_path:
        print('Warning: vllm.platforms.interface.py not found')
        return False
    
    # 读取文件内容
    with open(interface_path, 'r') as f:
        content = f.read()
    
    # 检查是否已经应用了补丁
    if 'import vllm._C_cache_ops' in content and 'import_kernels' in content:
        # 检查是否在 import_kernels 方法中
        import_kernels_start = content.find('def import_kernels')
        cache_ops_import = content.find('import vllm._C_cache_ops', import_kernels_start)
        if cache_ops_import > import_kernels_start and cache_ops_import < import_kernels_start + 500:
            print(f'Patch already applied to {interface_path}')
            return True
    
    # 查找要替换的代码
    old_import_kernels = '''    @classmethod
    def import_kernels(cls) -> None:
        """Import any platform-specific C kernels."""
        try:
            import vllm._C  # noqa: F401
        except ImportError as e:
            logger.warning("Failed to import from vllm._C: %r", e)
        with contextlib.suppress(ImportError):
            import vllm._moe_C  # noqa: F401'''
    
    # 新的代码（添加 cache ops 导入）
    new_import_kernels = '''    @classmethod
    def import_kernels(cls) -> None:
        """Import any platform-specific C kernels."""
        try:
            import vllm._C  # noqa: F401
        except ImportError as e:
            logger.warning("Failed to import from vllm._C: %r", e)
        with contextlib.suppress(ImportError):
            import vllm._moe_C  # noqa: F401
        with contextlib.suppress(ImportError):
            import vllm._C_cache_ops  # noqa: F401'''
    
    # 替换
    if old_import_kernels in content:
        content = content.replace(old_import_kernels, new_import_kernels)
    else:
        print(f'Warning: Target code not found in {interface_path}')
        return False
    
    # 写回文件
    with open(interface_path, 'w') as f:
        f.write(content)
    
    print(f'Successfully patched {interface_path}')
    return True

if __name__ == '__main__':
    success = patch_platforms_import_kernels()
    sys.exit(0 if success else 1)

