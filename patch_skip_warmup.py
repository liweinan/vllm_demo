#!/usr/bin/env python3
"""
修复 vLLM CPU warmup：跳过 warmup 阶段以减少内存使用
"""
import os
import sys

def patch_skip_warmup():
    """在 vLLM 的 cpu_model_runner.py 中跳过 warmup"""
    # 查找 vllm.v1.worker.cpu_model_runner.py 文件
    cpu_model_runner_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', 'v1', 'worker', 'cpu_model_runner.py')
        if os.path.exists(test_path):
            cpu_model_runner_path = test_path
            break

    if not cpu_model_runner_path:
        print('Warning: vllm.v1.worker.cpu_model_runner.py not found')
        return False

    # 读取文件内容
    with open(cpu_model_runner_path, 'r') as f:
        content = f.read()

    # 检查是否已经应用了补丁
    if 'def warming_up_model(self) -> None:' in content and 'logger.info("Skipping warmup to reduce memory usage...")' in content:
        print(f'Patch already applied to {cpu_model_runner_path}')
        return True

    # 查找要替换的代码
    old_warming_up = '''    def warming_up_model(self) -> None:
        logger.info("Warming up model for the compilation...")
        # Only generate graph for the generic shape
        with _set_global_compilation_settings(self.vllm_config):
            self._dummy_run(
                min(
                    max(16, self.max_num_reqs),
                    self.scheduler_config.max_num_batched_tokens,
                )
            )

        logger.info("Warming up done.")'''

    # 新的代码（跳过 warmup）
    new_warming_up = '''    def warming_up_model(self) -> None:
        logger.info("Skipping warmup to reduce memory usage...")
        # Skip warmup to avoid OOM during initialization
        # The model will be warmed up on first request instead
        # with _set_global_compilation_settings(self.vllm_config):
        #     self._dummy_run(
        #         min(
        #             max(16, self.max_num_reqs),
        #             self.scheduler_config.max_num_batched_tokens,
        #         )
        #     )

        logger.info("Warmup skipped.")'''

    # 替换
    if old_warming_up in content:
        content = content.replace(old_warming_up, new_warming_up)
    else:
        print(f'Warning: Target code not found in {cpu_model_runner_path}')
        return False

    # 写回文件
    with open(cpu_model_runner_path, 'w') as f:
        f.write(content)

    print(f'Successfully patched {cpu_model_runner_path}')
    return True

if __name__ == '__main__':
    success = patch_skip_warmup()
    sys.exit(0 if success else 1)

