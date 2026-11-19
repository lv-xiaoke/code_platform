"""Trusted child bootstrap: apply limits before loading a user's program."""
import resource
import runpy
import sys

resource.setrlimit(resource.RLIMIT_CPU, (3, 4))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
script = sys.argv[1]
sys.argv = [script]
runpy.run_path(script, run_name='__main__')
