#!/usr/bin/env python3
"""
修复 vLLM CPU 平台检测：添加对 VLLM_TARGET_DEVICE 环境变量的检查
"""
import os
import sys

def patch_vllm_platforms():
    """在 vLLM 的 platforms/__init__.py 中添加 VLLM_TARGET_DEVICE 检查"""
    # 查找 vllm.platforms.__init__.py 文件
    vllm_platforms_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', 'platforms', '__init__.py')
        if os.path.exists(test_path):
            vllm_platforms_path = test_path
            break
    
    if not vllm_platforms_path:
        print('Warning: vllm.platforms.__init__.py not found')
        return False
    
    # 读取文件内容
    with open(vllm_platforms_path, 'r') as f:
        content = f.read()
    
    # 检查是否已经应用了补丁
    if 'VLLM_TARGET_DEVICE' in content and 'Confirmed CPU platform is available because VLLM_TARGET_DEVICE=cpu' in content:
        print(f'Patch already applied to {vllm_platforms_path}')
        return True
    
    # 查找要替换的代码
    old_check = 'is_cpu = vllm_version_matches_substr("cpu")'
    if old_check not in content:
        print(f'Warning: Target code not found in {vllm_platforms_path}')
        return False
    
    # 新的代码（添加 VLLM_TARGET_DEVICE 检查）
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
    
    # 替换
    content = content.replace(old_check, new_check)
    
    # 写回文件
    with open(vllm_platforms_path, 'w') as f:
        f.write(content)
    
    print(f'Successfully patched {vllm_platforms_path}')
    return True

if __name__ == '__main__':
    success = patch_vllm_platforms()
    sys.exit(0 if success else 1)

