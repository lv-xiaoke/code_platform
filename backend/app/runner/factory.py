import os


def runner_kind():
    kind = os.environ.get('CODETOP_RUNNER', 'native')
    if kind not in ('native', 'docker'):
        raise ValueError('CODETOP_RUNNER 只能为 native 或 docker')
    return kind


def create_runner(artifact_root, *, interactive=False):
    if runner_kind() == 'native':
        if interactive:
            from .terminal_native import NativeTerminalRunner
            return NativeTerminalRunner(artifact_root)
        from .native import NativeRunner
        return NativeRunner(artifact_root)
    if interactive:
        from .terminal_docker import InteractiveDockerRunner
        return InteractiveDockerRunner(artifact_root)
    from .docker import DockerRunner
    return DockerRunner(artifact_root)
