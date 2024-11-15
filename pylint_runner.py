#!/usr/bin/env python3
"""
This script runs pylint on the project and outputs the warnings
using different formats:
- GitHub Actions Error strings (turned into annotations by GitHub)
- Markdown Reports for showing them in the GitHub Actions Summary
- a pylint.txt for diff-quality to ensure no regressions in diffs.

The output for GitHub of this script is filtered for focussing on severe warnings.
Especially, the encoding warnings are important.

On stdout, the format used by GitHub to generate error annotations us used.
These error annotations are shown on the top of the GitHub Action summary page
and are also shown in the diff view at the their code locations.

It also generates a markdown report including two Markdown
tables (one for summary, one with the individual errors)
which can be viewed locally and is also shown in the GitHub
Action's Summary Report.
"""

import json
import os
import sys
from glob import glob
from io import StringIO
from typing import List, TextIO

import pandas as pd  # type: ignore[import]
from pylint.lint import Run  # type: ignore[import]
from pylint.reporters import JSONReporter  # type: ignore[import]
from toml import load


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
        dot_pos = r["obj"].rindex(".") + 1
    except ValueError:
        dot_pos = 0
    r["obj"] = r["obj"][dot_pos:].split("test_")[-1][:16]


suppress_msg = ["Unused variable 'e'"]  # type: list[str]
error_syms = [
    "no-value-for-parameter",
    "unexpected-keyword-arg",
]
notice_syms = [
    "attribute-defined-outside-init",
    "bare-except",
    "broad-exception-raised",
    "duplicate-code",
    "duplicate-except",
    "super-init-not-called",
    "fixme",
    "no-member",
    "pointless-string-statement",
    "unnecessary-lambda",
    "unnecessary-semicolon",
    "unused-import",
    "unused-variable",
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
# Reference: pylint3 removed the --py3k checker "because the transition is behind us":
# https://github.com/pylint-dev/pylint/blob/main/pylint/extensions/eq_without_hash.py
#
# But some checks are still useful in python3 after all, and this is the remnant of it.
# Documentation on it:
# https://pylint.readthedocs.io/en/latest/user_guide/messages/warning/eq-without-hash.html
#
pylint_options: List[str] = [
    "--load-plugins", "pylint.extensions.eq_without_hash"
]


def pylint_project(check_dirs: List[str], errorlog: TextIO, branch_url: str):
    pylint_overview = []
    pylint_results = []
    pylint_paths = []
    config = load("pyproject.toml")
    pylint = config["tool"].get("github_pylint")
    suppress_sym = pylint.get("suppressed_syms", []) if pylint else []
    check_patterns = [p + "/**/*.py" for p in check_dirs]
    list(map(lambda x: pylint_paths.extend(glob(x, recursive=True)), check_patterns))
    score_sum = 0.0
    smells_total = 0
    for path in pylint_paths:
        filename = path.rsplit("/", maxsplit=1)[-1]
        if filename in ["__init__.py", ".pylintrc"]:
            continue
        reporter_buffer = StringIO()
        results = Run(
            [path] + pylint_options,
            reporter=JSONReporter(reporter_buffer),
            exit=False,
        )
        score = results.linter.stats.global_note
        file_results = json.loads(reporter_buffer.getvalue())
        if not file_results:
            continue
        filtered_file_results = []
        message_ids = {}
        linktext = filename.split(".")[0]
        for r in file_results:
            cls = r["type"]
            sym = r["symbol"]
            msg = r["message"]
            msg_id = r["message-id"]
            lineno = r["line"]
            # Write errors in the format for diff-quality to check against regressions:
            errorlog.write(f"{path}:{lineno}: [{msg_id}({sym}), {r['obj']}] {msg}\n")
            if not msg:
                continue

            if sym in suppress_sym or msg in suppress_msg:
                continue

            if sym in error_syms:
                msg = "Error: " + msg
                cls = "error"

            elif sym in notice_syms:
                msg = "Notice: " + msg
                cls = "notice"

            elif cls in ("convention", "refactor"):
                msg = cls.title() + ": " + msg
                cls = "notice"

            message_ids[sym] = ""  # Populate a dict of the pylint message symbols seen in this file
            # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-notice-message
            endline = r["endLine"]
            end = f",endLine={endline}" if endline and endline != lineno else ""
            print(
                f"::{cls} file={path},line={lineno}{end},"
                f"title=pylint {msg_id}: {sym}::{msg}",
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
                "filepath": f"[`{path.split('/')[-1]}`]({branch_url}/{path})",
                "smells": smells_count,
                "symbols": " ".join(message_ids.keys()),
                "score": float(round(score, 1)),  # There are some ints among the floats
            }
        )
    avg_score = score_sum / len(pylint_overview) if pylint_overview else 10.0
    pylint_overview.append(
        {
            "filepath": "total",
            "smells": smells_total,
            "symbols": "",
            "score": round(avg_score, 1),
        }
    )
    return pd.DataFrame(pylint_overview), pd.DataFrame(pylint_results)


def main(dirs: List[str], output_file: str, pylint_logfile: str, branch_url: str):
    """Send pylint errors, warnings, notices to stdout. Github shows 10 of each type

    Args:
        module_dir (str): subdirectory of the module, e.g. "xcp"
        output_file (str): output file path for the markdown summary table
        branch_url (str): _url of the branch for file links in the summary table
    """
    with open(pylint_logfile, "w", encoding="utf-8") as txt_out:
        panda_overview, panda_results = pylint_project(dirs, txt_out, branch_url)

    # Write the panda table to a markdown output file:
    summary_file = output_file or os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return

    with open(summary_file, "w", encoding="utf-8") as fp:
        write_results_as_markdown_tables(branch_url, fp, panda_overview, panda_results)


def write_results_as_markdown_tables(branch_url, fp, panda_overview, panda_results):
    me = os.path.basename(__file__)
    link = f"[{me}]({branch_url}/{me})"
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#multiline-markdown-content
    fp.write(f"### PyLint breakdown from {link} on **xcp/\\*\\*/*.py**\n")
    fp.write(panda_overview.to_markdown())
    fp.write(f"\n### PyLint results from {link} on **xcp/\\*\\*/*.py**\n")
    fp.write(panda_results.to_markdown())


if __name__ == "__main__":
    github_blob_url = "https://github.com/xenserver/python-libs/blob/master"
    server_url = os.environ.get("GITHUB_SERVER_URL", None)
    repository = os.environ.get("GITHUB_REPOSITORY", None)
    if server_url and repository:
        # https://github.com/orgs/community/discussions/5251 only set on Pull requests:
        branch = os.environ.get("GITHUB_HEAD_REF", None) or os.environ.get("GITHUB_REF_NAME", None)
        github_blob_url = f"{server_url}/{repository}/blob/{branch}"

    # Like the previous run-pylint.sh, check the xcp module by default:
    dirs_to_check = sys.argv[1:] if len(sys.argv) > 1 else ["xcp", "tests"]

    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY", ".tox/pylint-summary-table.md")

    #
    # Generate a pylint.txt in the format expected by diff-quality to get pylint
    # warnings for the git diff of the current branch (to master). This checks
    # against regressions and is called by the lint environment in tox.ini for CI:
    #
    pylint_txt = os.environ.get("ENVLOGDIR", ".tox") + "/pylint.txt"

    print("Checking:", str(dirs_to_check) + "; Writing report to:", step_summary)
    main(dirs_to_check, step_summary, pylint_txt, github_blob_url)
