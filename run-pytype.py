#!/usr/bin/env python
import os
import re
import shlex
import sys
from logging import INFO, basicConfig, info
from subprocess import DEVNULL, PIPE, Popen
from typing import TextIO

import pandas as pd


def run_pytype(command: list, branch_url: str, errorlog: TextIO, results):
    info(" ".join(shlex.quote(arg) for arg in command))
    # When run in tox, pytype dumps debug messages to stderr. Point stderr to /dev/null:
    popen = Popen(command, stdout=PIPE, stderr=DEVNULL, universal_newlines=True)
    error = ""
    row = {}
    while True:
        if not popen.stdout:
            break
        line = popen.stdout.readline()
        if line == "" and popen.poll() is not None:
            break
        line = line.rstrip()

        if not line or line[0] == "/" or line.startswith("FAILED:"):
            continue
        if line[0] == "[":
            pos = line.rfind(os.getcwd())
            if pos > 0:
                printfrom = pos + len(os.getcwd()) + 1
            else:
                printfrom = line.index("]") + 2
            info("PROGRESS: " + line[1:].split("]")[0] + ": " + line[printfrom:])
            continue
        elif line.startswith("ninja: "):
            line = line[7:]
        if (
            line.startswith("Entering")
            or line.startswith("Leaving")
            or line.startswith("Computing")
            or line.startswith("Analyzing")
        ):
            continue
        info(line)
        if row:
            if line == "" or line[0] == " " or line.startswith("For more details, see"):
                if line:
                    if line.startswith("For more details, see"):
                        row["Error code"] = f"[{row['Error code']}]({line[22:]})"
                        error += " " + line[22:]
                    else:
                        if not row["Error description"]:
                            row["Error description"] = line.lstrip()
                        else:
                            row["Error description"] += " " + line.lstrip()
                        error += ", " + line
                continue
            errorlog.write(
                error
                + " (you should find an entry in the pytype results with links below)\n"
            )
            results.append(row)
            row = {}
            error = ""
        match = re.match(
            r'File ".*libs/([^"]+)", line (\S+), in ([^:]+): (.*) \[(\S+)\]', line
        )
        if match:
            lineno = match.group(2)
            code = match.group(5)
            func = match.group(3)
            msg = match.group(4)
            msg_splitpos = msg.find(" ", 21)
            file = match.group(1)
            linktext = os.path.basename(file).split(".")[0]
            source_link = f"[`{linktext}`]({branch_url}/{file}#L{lineno})"
            row = {
                "Location": source_link,
                "Function": f"`{func}`",
                "Error code": code,
                "Error message": msg[:msg_splitpos] + "<br>" + msg[msg_splitpos + 1 :],
                "Error description": "",
            }
            # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-error-message
            error = f"::error file={file},line={lineno},title=pytype: {code}::{msg}"
    if popen.stdout:
        popen.stdout.close()
    return_code = popen.wait()
    return return_code, results


def to_markdown(me, fp, results, branch_url):
    mylink = f"[`{me}`]({branch_url}/{me}.py)"
    pytype_link = "[`pytype`](https://google.github.io/pytype)"
    fp.write(f"\n### TODO/FIXME: Selected {pytype_link} errors by {mylink}:\n")
    fp.write(pd.DataFrame(results).to_markdown())
    fp.write("\n")


def main(me: str, branch_url: str):
    """Send pytype errors to stdout.

    Args:
        module_dir (str): subdirectory of the module, e.g. "xcp"
        output_file (str): output file path for the markdown summary table
        branch_url (str): _url of the branch for file links in the summary table
    """
    never = (
        "xcp/bootloader.py",
        "xcp/repository.py",
        "tests/test_ifrename_logic.py",
        "tests/test_xmlunwrap.py",
    )
    excludes = [
        "xcp/cmd.py",
        "xcp/net/ip.py",
    ]
    errors_in = excludes.copy()
    errors_in.extend(never)
    base = [
        "pytype",
        "-k",
        "--config",
        ".github/workflows/pytype.cfg",
    ]
    command = base.copy()
    command.extend(["--exclude", " ".join(errors_in)])

    def call_pytype(outfp):
        exit_code, results = run_pytype(command, branch_url, sys.stderr, [])
        for exclude in excludes:
            command2 = base.copy()
            command2.append(exclude)
            err_code, results = run_pytype(command2, branch_url, outfp, results)
            if err_code == 0:
                print("No errors in", exclude)
        return exit_code, results

    exit_code, results = call_pytype(sys.stdout)

    # Write the panda dable to a markdown output file:
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", None)
    if summary_file:
        with open(summary_file, "w", encoding="utf-8") as fp:
            to_markdown(me, fp, results, branch_url)
    else:
        to_markdown(me, sys.stdout, results, branch_url)
    sys.exit(exit_code)


if __name__ == "__main__":
    scriptname = os.path.basename(__file__).split(".")[0]
    basicConfig(format=scriptname + ": %(message)s", level=INFO)
    filelink_baseurl = "https://github.com/xenserver/python-libs/blob/master"
    server_url = os.environ.get("GITHUB_SERVER_URL", None)
    repository = os.environ.get("GITHUB_REPOSITORY", None)
    if server_url and repository:
        # https://github.com/orgs/community/discussions/5251 only set on Pull requests:
        branch = os.environ.get("GITHUB_HEAD_REF", None)
        if not branch:
            # Always set but set to num/merge on PR, but to branch on pushes:
            branch = os.environ.get("GITHUB_REF_NAME", None)
        filelink_baseurl = f"{server_url}/{repository}/blob/{branch}"
    main(scriptname, filelink_baseurl)
