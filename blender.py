import subprocess
import sys
import textwrap
import json
import re
from pathlib import Path

_START_MARKER = "START>"
_END_MARKER = "<END"
_MATCHER = re.compile(f"{_START_MARKER}(.*){_END_MARKER}")


def dump_dict(name):
    return f"""import json; print(f"{_START_MARKER}{{json.dumps({name})}}{_END_MARKER}")"""


def recover_dict(completed: subprocess.CompletedProcess):
    json_str = _MATCHER.search(completed.stdout).group(1)
    return json.loads(json_str)


# `capture_output` can also be used as a semi-silent mode - output will only be printed if CalledProcessError occurs.
def run_blender(
    blender,
    input_file,
    python_code,
    additional_popenargs=None,
    capture_output=False
) -> subprocess.CompletedProcess:
    python_code = textwrap.dedent(python_code)
    # If you put `--python-expr` before the input file then you'll get values from the default cube scene.
    # And if `cwd` isn't set then Blender can't find resources with relative paths.
    popenargs = [
        blender,
        "--factory-startup",
        "--background",
        input_file,
        "--python-expr", python_code
    ] + (additional_popenargs if additional_popenargs is not None else [])
    cwd = Path(input_file).parent  # Surprisingly, os.path.dirname("foo") returns "" rather than "."
    try:
        return subprocess.run(popenargs, cwd=cwd, check=True, capture_output=capture_output, text=True)
    except subprocess.CalledProcessError as e:
        if capture_output:
            print(e.stdout)
            print(e.stderr, file=sys.stderr)
        raise e
