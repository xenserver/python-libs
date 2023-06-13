#!/usr/bin/env python
import os
import re
import shlex
import sys
from logging import INFO, basicConfig, info
from subprocess import DEVNULL, PIPE, Popen
from typing import List, TextIO, Tuple

import pandas as pd  # type: ignore[import]
from toml import load


def generate_github_annotation(match: re.Match, branch_url: str) -> str:
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
    return f"::error file={file},line={lineno},title=pytype: {code}::{msg}"


def filter_line(line, row):
    if line.startswith("For more details, see"):
        row["Error code"] = f"[{row['Error code']}]({line[22:]})"
        return " " + line[22:]
    if not row["Error description"]:
        row["Error description"] = line.lstrip()
    else:
        row["Error description"] += " " + line.lstrip()
    return ", " + line


def skip_uninteresting_lines(line: str) -> bool:
    if not line or line[0] == "/" or line.startswith("FAILED:"):
        return True
    if line[0] == "[":
        pos = line.rfind(os.getcwd())
        printfrom = pos + len(os.getcwd()) + 1 if pos > 0 else line.index("]") + 2
        info("PROGRESS: " + line[1:].split("]")[0] + ": " + line[printfrom:])
        return True
    if line.startswith("ninja: "):
        line = line[7:]
    return bool(
        (
            line.startswith("Entering")
            or line.startswith("Leaving")
            or line.startswith("Computing")
            or line.startswith("Analyzing")
        )
    )


def run_pytype(command: List[str], branch_url: str, errorlog: TextIO, results):
    info(" ".join(shlex.quote(arg) for arg in command))
    # When run in tox, pytype dumps debug messages to stderr. Point stderr to /dev/null:
    popen = Popen(command, stdout=PIPE, stderr=DEVNULL, universal_newlines=True)
    error = ""
    row = {}  # type: dict[str, str]
    while popen.stdout:
        line = popen.stdout.readline()
        if line == "" and popen.poll() is not None:
            break
        line = line.rstrip()
        if skip_uninteresting_lines(line):
            continue
        info(line)
        if row:
            if line == "" or line[0] == " " or line.startswith("For more details, see"):
                if line:
                    error += filter_line(line, row)
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
            error = generate_github_annotation(match, branch_url)
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


def pytype_with_github_annotations_to_stdout(me: str, xfail_files: list, branch_url: str):
    """Send pytype errors to stdout.

    Args:
        module_dir (str): subdirectory of the module, e.g. "xcp"
        output_file (str): output file path for the markdown summary table
        branch_url (str): _url of the branch for file links in the summary table
    """
    base = [
        "pytype",
        "-j",
        "auto",
        "-k",
        "--config",
        ".github/workflows/pytype.cfg",
    ]
    command = base.copy()
    if xfail_files:
        command.extend(["--exclude", " ".join(xfail_files)])

    def call_pytype(outfp):
        exit_code, results = run_pytype(command, branch_url, sys.stderr, [])
        for xfail_file in xfail_files:
            command2 = base.copy()
            command2.append(xfail_file)
            err_code, results = run_pytype(command2, branch_url, outfp, results)
            if err_code == 0:
                print("No errors in", xfail_file)
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


def setup_and_run_pytype_action(scriptname: str):
    config = load("pyproject.toml")
    pytype = config["tool"].get("pytype")
    xfail_files = pytype.get("xfail", []) if pytype else []
    repository_url = config["project"]["urls"]["repository"].strip(" /")
    filelink_baseurl = repository_url + "/blob/master"
    # When running as a GitHub action, we want to use URL of the fork with the GitHub action:
    server_url = os.environ.get("GITHUB_SERVER_URL", None)
    repository = os.environ.get("GITHUB_REPOSITORY", None)
    if server_url and repository:
        # https://github.com/orgs/community/discussions/5251 only set on Pull requests:
        branch = os.environ.get("GITHUB_HEAD_REF", None) or os.environ.get("GITHUB_REF_NAME", None)
        filelink_baseurl = f"{server_url}/{repository}/blob/{branch}"
    pytype_with_github_annotations_to_stdout(scriptname, xfail_files, filelink_baseurl)


if __name__ == "__main__":
    scriptname = os.path.basename(__file__).split(".")[0]
    basicConfig(format=scriptname + ": %(message)s", level=INFO)
    setup_and_run_pytype_action(scriptname)
