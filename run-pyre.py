#!/usr/bin/env python
"""
Run a one-time pyre static analysis check without needing a .pyre_configuration
Gets the paths dynamically so it can be used in tox and GitHub CI
"""
import os
import sys
import time

import mock

me = os.path.basename(__file__) + ":"

pyre_typesched = os.environ.get("PYRE_TYPESHED", None)
if pyre_typesched and os.path.exists(pyre_typesched + "/stdlib/os/path.pyi"):
    print("Using {env:PYRE_TYPESHED}:", pyre_typesched)
else:
    pyre_typesched = sys.path[-1] + "/mypy/typeshed"
    if os.path.exists(pyre_typesched + "/stdlib/os/path.pyi"):
        print("Using python_lib:", pyre_typesched)
    else:
        pyre_typesched = "/tmp/typeshed"
        if os.path.exists(pyre_typesched + "/stdlib/os/path.pyi"):
            print("Using:", pyre_typesched)
        else:
            clone = "git clone --depth 1 https://github.com/python/typeshed "
            print(me, "Falling back to:", clone + pyre_typesched)
            ret = os.system(clone + pyre_typesched)
            if ret or not os.path.exists(pyre_typesched + "/stdlib/os/path.pyi"):
                print(me, "Could not find or clone typeshed, giving up.")
                sys.exit(0)

command = (
    "pyre",
    "--source-directory",
    "xcp",
    "--source-directory",
    "tests",
    "--search-path",
    "stubs",
    "--search-path",
    ".",
    "--search-path",
    os.path.dirname(mock.__path__[0]),  # pyright: ignore
    "--typeshed",
    pyre_typesched,
    "check",
)
cmd = " ".join(command)
print(me, "Running:", cmd)
start_time = time.time()
ret = os.system(cmd)
duration = time.time() - start_time
r = os.waitstatus_to_exitcode(ret)
if r == 0:
    print(me, f"OK pyre took: {duration:.1f}s")
else:
    print(me, "Ran:", cmd)
    print(me, "exit code:", r)
    if os.environ.get("ACT", None):
        time.sleep(10)
sys.exit(r)
