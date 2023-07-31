#
# Temporary compatibility `setup27.py` as workaround to compensate for
# for missing pip2 in XenServer Koji until Python2 support can be dropped:
#
# It is named setup27.py so it is only used when called explicitly:
#
# The installation for Python2 uses `python2 setup27.py install`!
#
from setuptools import setup

setup(
    name="python-libs",
    description="Common XenServer Python classes for Python 2.7",
    packages=["xcp", "xcp.net", "xcp.net.ifrename"],
    requires=[
        "branding",
        # These are the new requires for Python 2.7
        # after adding Python3 support, and the CentOS7 setuptools
        # in the current XenServer Koji are <36.2, which would updating
        # to support the syntax for ;python_version < "3.0":
        # https://hynek.me/articles/conditional-python-dependencies/
        "configparser",
        "pyliblzma",
        "six",
        # To install for Python3, use: `pip install .`
        # (pip install uses pyproject.toml which replaces setup.py)!
    ],
)
