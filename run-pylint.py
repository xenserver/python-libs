#!/usr/bin/env python3
"""
This script runs pylint on the project and outputs the warnings
using different formats:
- GitHub Actions Error strings (turned into annotations by GitHub)
- Markdown Reports for showing them in the GitHub Actions Summary
- a pylint.txt for diff-quality to ensure no regressions in diffs.

Pylint for Python2 does not support JSONReporter, so this wrapper only supports
the native Python3 checks, not the 2to3 conversion checks selected by the --py3k
options provied only in the Pylint for Python2.
The older pylint-2.16 could be checked if it supports both.

The output for GitHub of this script is fitered for putting the
focus on severen warnings for the Python3 transition, expecially
the encoding warnings are important.

On stdout, the format used by GitHub to generate error annotations us used.
These error annotations are shown on the top of the GitHub Action summary page
and are also shown in the diff view at the their code locations.

It also generates a markdown report including two Markdown
tables (one for summary, one with the individual erros)
which can be viewed locally and is also shown in the GitHub
Action's Summary Report.
"""

import json
import os
import sys
from glob import glob
from io import StringIO, TextIOWrapper
from typing import List

from pylint.lint import Run  # type: ignore
from pylint.reporters import JSONReporter  # tpe: ignore

import pandas as pd


def del_dict_keys(r, *args):
    for arg in args:
        r.pop(arg, None)


def cleanup_results_dict(r, sym):
    del_dict_keys(
        r,
        "module",
        "column",
        "endColumn",
        "message-id",
        "endLine",
        "type",
        "line",
    )
    r["symbol"] = sym[:32]
    r["message"] = r["message"][:96]
    try:
        dotpos = r["obj"].rindex(".") + 1
    except ValueError:
        dotpos = 0
    r["obj"] = r["obj"][dotpos:][:16]


suppress_msg = ["Consi", "Unnec", "Unuse", "Use l", "Unkno", "Unrec", "Insta"]
suppress_sym = [
    "attribute-defined-outside-init",
    "bare-except",
    "broad-exception-raised",
    # "duplicate-except",
    "super-init-not-called",
]
notice_syms = [
    "fixme",
    "no-member",
    "unexpected-keyword-arg",
    "assignment-from-no-return",
]

#
# The now-removed 2to3-specific option --py3k was written to warn about open TODOs
# for Python2 to Python3 transition, but the Python2 to Python3 checkers have been
# removed since.
#
# These checks warn about specific issues, which are usually real issues which
# must be fixed, so it is useful to run, and enforce it to be successful in CI.
#
# They are aligned to what 2to3 does, but 2to3 cannot fix all of them, for example:
# - "Implementing __eq__ without also implementing __hash__"
#   (python2 -m pylint --py3k found this in xcp/version.py)
#
# This is illegal according to:
# https://docs.python.org/3/reference/datamodel.html#object.__hash__
#
# Reference: pylint3 removed the --py3k checker "because the transition is bedind us":
# https://github.com/pylint-dev/pylint/blob/main/pylint/extensions/eq_without_hash.py
#
# But some checks are still useful in python3 after all, and this is the remnant of it.
# Documentation on it:
# https://pylint.readthedocs.io/en/latest/user_guide/messages/warning/eq-without-hash.html
#
pylint_options: List[str] = [
    "--load-plugins", "pylint.extensions.eq_without_hash",
]

def pylint_project(module_path: str, errorlog: TextIOWrapper, branch_url: str):

    pylint_overview = []
    pylint_results = []
    glob_pattern = os.path.join(module_path, "**", "*.py")
    score_sum = 0.0
    smells_total = 0
    for path in glob(glob_pattern, recursive=True):
        filename = path.rsplit("/", maxsplit=1)[-1]
        if filename in ["__init__.py", "pylintrc"]:
            continue
        reporter_buffer = StringIO()
        results = Run(
            [path] + pylint_options,
            reporter=JSONReporter(reporter_buffer),
            do_exit=False,
        )
        score = results.linter.stats.global_note
        file_results = json.loads(reporter_buffer.getvalue())
        if not file_results:
            continue
        filtered_file_results = []
        error_summary = {}
        linktext = filename.split(".")[0]
        for r in file_results:
            type = r["type"]
            sym = r["symbol"]
            msg = r["message"]
            msg_id = r["message-id"]
            lineno = r["line"]
            # Write errors in the format for diff-quality to check against regressions:
            errorlog.write(f"{path}:{lineno}: [{msg_id}({sym}), {r['obj']}] {msg}\n")
            # For suggestions to fix existing warnings, be more focussed on serverity:
            if not msg or type in ("convention", "refactor"):
                continue
            if sym in suppress_sym or msg[:5] in suppress_msg:
                continue
            if sym in notice_syms:
                type = "notice"
            else:  # For errors, collect the seen symbolic message ids as .keys()
                error_summary[sym] = 0
            # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-notice-message
            print(
                f"::{type} file={path},line={lineno},endLine={r['endLine']},"
                f"title=pylint {msg_id}: {sym}::{msg}"
            )
            r["path"] = f"[{linktext}]({branch_url}/{path}#L{lineno})"
            cleanup_results_dict(r, sym)
            filtered_file_results.append(r)

        pylint_results.extend(filtered_file_results)
        smells_count = len(filtered_file_results)
        smells_total += smells_count
        score_sum += score

        pylint_overview.append(
            {
                "filepath": f"[`{path[4:]}`]({branch_url}/{path})",
                "smells": smells_count,
                "symbols": " ".join(error_summary.keys()),
                "score": float(round(score, 1)),  # There are some ints among the floats
            }
        )
    avg_score = score_sum / len(pylint_overview)
    pylint_overview.append(
        {
            "filepath": "total",
            "smells": smells_total,
            "symbols": "",
            "score": round(avg_score, 1),
        }
    )
    return pd.DataFrame(pylint_overview), pd.DataFrame(pylint_results)  # , avg_score


def main(module_dir: str, output_file: str, pylint_txt: str, branch_url: str):
    """Send pylint errors, warnings, notices to stdout. Github shows 10 of each type

    Args:
        module_dir (str): subdirectory of the module, e.g. "xcp"
        output_file (str): output file path for the markdown summary table
        branch_url (str): _url of the branch for file links in the summary table
    """
    with open(pylint_txt, "w", encoding="utf-8") as txt_out:
        panda_overview, panda_results = pylint_project(module_dir, txt_out, branch_url)

    # Write the panda dable to a markdown output file:
    summary_file = output_file or os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return

    with open(summary_file, "w", encoding="utf-8") as fp:
        me = os.path.basename(__file__)
        mylink = f"[{me}]({branch_url}/{me})"
        # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#multiline-markdown-content
        fp.write(f"### PyLint breakdown from {mylink} on **xcp/\\*\\*/*.py**\n")
        fp.write(panda_overview.to_markdown())
        fp.write(f"\n### PyLint results from {mylink} on **xcp/\\*\\*/*.py**\n")
        fp.write(panda_results.to_markdown())


if __name__ == "__main__":
    ghblob_url = "https://github.com/xenserver/python-libs/blob/master"
    server_url = os.environ.get("GITHUB_SERVER_URL", None)
    repository = os.environ.get("GITHUB_REPOSITORY", None)
    if server_url and repository:
        # https://github.com/orgs/community/discussions/5251 only set on Pull requests:
        branch = os.environ.get("GITHUB_HEAD_REF", None)
        if not branch:
            # Always set but set to num/merge on PR, but to branch on pushes:
            branch = os.environ.get("GITHUB_REF_NAME", None)
        ghblob_url = f"{server_url}/{repository}/blob/{branch}"

    # Like the previous run-pylint.sh, check the xcp module by default:
    py_module_dir = sys.argv[1] if len(sys.argv) > 1 else "xcp"

    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY", ".tox/pylint-summary-table.md")

    #
    # Generate a pylint.txt in the format expected by diff-quality to get pylint
    # warnings for the git diff of the current branch (to master). This checks
    # against regressions and is called by the lint environment in tox.ini for CI:
    #
    pylint_txt = os.environ.get("ENVLOGDIR", ".tox") + "/pylint.txt"

    print("Checking:", py_module_dir + ", Writing report to:", step_summary)
    main(py_module_dir, step_summary, pylint_txt, ghblob_url)
