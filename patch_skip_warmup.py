#!/usr/bin/env python3
"""
Fix vLLM CPU warmup: skip warmup phase to reduce memory usage
"""
import os
import sys

def patch_skip_warmup():
    """Skip warmup in vLLM's cpu_model_runner.py"""
    # Find vllm.v1.worker.cpu_model_runner.py file
    cpu_model_runner_path = None
    for path in sys.path:
        test_path = os.path.join(path, 'vllm', 'v1', 'worker', 'cpu_model_runner.py')
        if os.path.exists(test_path):
            cpu_model_runner_path = test_path
            break

    if not cpu_model_runner_path:
        print('Warning: vllm.v1.worker.cpu_model_runner.py not found')
        return False

    # Read file content
    with open(cpu_model_runner_path, 'r') as f:
        content = f.read()
    
    # Check if patch already applied
    if 'def warming_up_model(self) -> None:' in content and 'logger.info("Skipping warmup to reduce memory usage...")' in content:
        print(f'Patch already applied to {cpu_model_runner_path}')
        return True
    
    # Find code to replace
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

    # New code (skip warmup)
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

    # Replace
    if old_warming_up in content:
        content = content.replace(old_warming_up, new_warming_up)
    else:
        print(f'Warning: Target code not found in {cpu_model_runner_path}')
        return False

    # Write back to file
    with open(cpu_model_runner_path, 'w') as f:
        f.write(content)

    print(f'Successfully patched {cpu_model_runner_path}')
    return True

if __name__ == '__main__':
    success = patch_skip_warmup()
    sys.exit(0 if success else 1)

