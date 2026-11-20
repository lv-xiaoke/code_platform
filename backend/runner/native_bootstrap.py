"""Trusted child bootstrap: apply limits before loading a user's program."""
import resource
import math
import os
import sys

cpu = math.ceil(float(sys.argv[2]))
argv = sys.argv[4:]
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024 * 1024, 256 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
os.execve(argv[0], argv, os.environ)
