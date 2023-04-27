#!/usr/bin/env python3
import json
import os
import sys
from glob import glob
from io import StringIO, TextIOWrapper
from typing import List

from pylint.lint import Run  # type: ignore
from pylint.reporters import JSONReporter  # type: ignore

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


def filter_results(r):
    msg = r["message"]
    typ = r["type"]
    if typ in ["convention", "refactor"] or not msg:
        return None, None, None
    sym = r["symbol"]
    return (
        (None, None, None)
        if sym in suppress_sym or msg[:5] in suppress_msg
        else (typ, sym, msg)
    )


def pylint_project(module_path: str, branch_url: str, errorlog: TextIOWrapper):
    pylint_options: List[str] = []
    pylint_overview = []
    pylint_results = []
    glob_pattern = os.path.join(module_path, "**", "*.py")
    score_sum = 0.0
    smell_sum = 0
    for filepath in glob(glob_pattern, recursive=True):
        filename = filepath.rsplit("/", maxsplit=1)[-1]
        if filename in ["__init__.py", "pylintrc"]:
            continue
        reporter_buffer = StringIO()
        results = Run(
            [filepath] + pylint_options,
            reporter=JSONReporter(reporter_buffer),
            do_exit=False,
        )
        score = results.linter.stats.global_note
        file_results = json.loads(reporter_buffer.getvalue())
        if not file_results:
            continue
        filtered_file_results = []
        filtered_messages = {}
        linktext = filename.split(".")[0]
        for r in file_results:
            typ, sym, msg = filter_results(r)
            if msg is None:
                continue
            print(typ, sym, msg)
            if sym in notice_syms:
                typ = "notice"
            else:
                filtered_messages[sym] = 0
            errorlog.write(
                f"::{typ} file={filepath},line={r['line']},endLine={r['endLine']},"
                f"title={sym}::{msg}\n"
            )
            r["path"] = f"[{linktext}]({branch_url}/{filepath}#L{r['line']})"
            cleanup_results_dict(r, sym)
            filtered_file_results.append(r)

        pylint_results.extend(filtered_file_results)
        smells = len(filtered_file_results)
        smell_sum += smells
        score_sum += score

        pylint_overview.append(
            {
                "filepath": f"[{filepath[4:]}]({branch_url}/{filepath})",
                "smells": smells,
                "symbols": " ".join(filtered_messages.keys()),
                "score": round(score, 3),
            }
        )
    avg_score = score_sum / len(pylint_overview)
    pylint_overview.append(
        {
            "filepath": "total",
            "smells": smell_sum,
            "symbols": "",
            "score": round(avg_score, 3),
        }
    )
    return pd.DataFrame(pylint_overview), pd.DataFrame(pylint_results)  # , avg_score


def main(module_dir: str, output_file: str, branch_url: str, errorlog_file: str):
    """Send pylint errors, warnings, notices to stdout. Github show show 10 of each

    Args:
        module_dir (str): subdirectory of the module, e.g. "xcp"
        output_file (str): output file path for the markdown summary table
        branch_url (str): _url of the branch for file links in the summary table
    """
    with open(errorlog_file, "a", encoding="utf-8") as errors:
        panda_overview, panda_results = pylint_project(module_dir, branch_url, errors)

    # print("### Overview")
    # print(panda_overview.to_markdown())
    # print("\n### Results")
    # print(panda_results.to_markdown())

    # Write the panda dable to a markdown output file:
    summary_file = output_file or os.environ.get("GITHUB_STEP_SUMMARY")
    scriptname = __file__.rsplit("/", maxsplit=1)[-1]
    mylink = f"[{scriptname}]({branch_url}/{scriptname})"
    if summary_file:
        with open(summary_file, "w", encoding="utf-8") as fp:
            fp.write(
                f"### PyLint breakdown from {mylink} on **xcp/\\*\\*/*.py**\n"
            )
            fp.write(panda_overview.to_markdown())

            fp.write(
                f"\n### PyLint results from {mylink} on **xcp/\\*\\*/*.py**\n"
            )
            fp.write(panda_results.to_markdown())


if __name__ == "__main__":
    default_branch_url = "https://github.com/xenserver/python-libs/blob/master"
    default_error_file = "/dev/stderr"

    py_module_dir = sys.argv[1] if len(sys.argv) > 1 else "xcp"
    gh_output_file = sys.argv[2] if len(sys.argv) > 2 else "pylint-summary-table.md"
    gh_branch_url = sys.argv[3] if len(sys.argv) > 3 else default_branch_url
    errorlog_path = sys.argv[4] if len(sys.argv) > 4 else default_error_file

    print(py_module_dir, gh_output_file, gh_branch_url, errorlog_path)
    main(py_module_dir, gh_output_file, gh_branch_url, errorlog_path)
