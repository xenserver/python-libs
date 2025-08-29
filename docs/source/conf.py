# Configuration file for the Sphinx documentation builder.
# -- Path setup -------------------------------------------------------------
import logging
import os
import sys

# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Add project root to sys.path for autodoc to find xcp modules and it allows
# to {include} the toplevel README.md files from their wrapper files here.
sys.path.insert(0, os.path.abspath("../.."))

# Add stubs directory to sys.path for stubs (xcp/bootloader.py needs a branding.py)
sys.path.insert(0, os.path.abspath("../../stubs"))

#
# To support Markdown-based documentation, Sphinx can use MyST-Parser.
# MyST-Parser is a Docutils bridge to markdown-it-py, a Python package
# for parsing the CommonMark Markdown flavor.
# See https://myst-parser.readthedocs.io/en/latest/ for details.
# Set the log level of markdown-it log categories to INFO to disable DEBUG
# logging and prevent flooding the logs with many 1000s of DEBUG messages:
#
logging.getLogger("markdown_it.rules_block").setLevel(logging.INFO)
logging.getLogger("markdown_it.rules_inline").setLevel(logging.INFO)
logging.getLogger("markdown_it").setLevel(logging.INFO)

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "python-libs"
copyright = "2025, Citrix Inc."
author = "Citrix Inc."
from datetime import datetime

release = datetime.now().strftime("%Y.%m.%d-%H%M")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "myst_parser",
]

myst_heading_anchors = 2
templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
