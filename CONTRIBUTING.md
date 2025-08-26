# Development setup

To run all tests and all supported static analysis tools, Python 3.11 is needed,
which matches the current Python version of XenServer 9.

Python 3.10 might work as well (when replacing the references in the config files with 3.10).
Python 3.12 and 3.13 can be used too, but not for running [pytype](https://github.com/google/pytype)
([it does not support 3.12 yet](https://google.github.io/pytype/support.html)).

On Ubuntu, you can install 3.11 (and also 3.12 and 3.13) from the widely-used Python support PPA:

```sh
sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update
sudo apt install -y python3.11 python3.12 python3.13
```

If 3.12 or 3.13 are found by [tox](https://tox.wiki), it will run the unit tests with them as well.

You can also use [uv to install Python versions](https://docs.astral.sh/uv/concepts/python-versions),
see below on a link and an example how to install uv.

## Do not use distro-privided Python CI tools

Python tools (other than the Python interpreters themself) provided by Linux distributions
are "always" out of date and do not work as required. If possible, uninstall/remove those,
even if your environment is based on Ubuntu 24.04. In addition, most problematically, the
distribution-provided Python tools are running using the default Pyton version of the
host system, which may not be compatible and can cause subtle errors.  (e.g. Python 3.12
or newer triggers unclear dependency errors in pytype because it is not supported yet)

## Create a virtual environment with the test dependencies

[Install `uv`](https://docs.astral.sh/uv/), either using `pip`/`pipx` or the
[installer](https://docs.astral.sh/uv/getting-started/installation/)
and install the extras groups that you need. Example:

```sh
pip install pipx
pipx install uv
uv venv --python 3.11 .uv-venv
. .uv-venv/bin/activate
uv pip install -r pyproject.toml --extra test mypy pytype pyright tox pre-commit
```

The older, slower way is to use pip-compile to the deps from `pyproject.toml`:

```bash
python -m venv .venv
. .venv/bin/activate
pip install pre-commit pip-tools==7.3.0
pip-compile --extra=test,mypy,pyright,pytype,tox -o - pyproject.toml | pip install -r /dev/stdin
```

## Running CI

These commands assume you installed the tools using the commands above in a Python 3.11 environment.

### Run pyright, watching for changes and automatically checking the change

```sh
pyright -w
```

### Run pytest with coverage (fine-grained, e.g. during test development)

```sh
pytest --cov -v --new-first -x --show-capture=all -rA [optional: files / select which tests to run]
```

### Watching and running tests on changes automatically using `pytest-watch` (`ptw`)

Install ptw in the Python environment using:

```sh
pip install pytest-watch
```

`ptw` watches changed files and runs `pytest` after changes are saved.
Run `ptw`, and pass the files to watch, e.g.:

```sh
ptw tests/test_*
```

### Run mypy (fine-grained, e.g. during development)

```sh
mypy [optionally pass the flags or files to select which tests to run]
```

### Run pylint (fine-grained, e.g. during development)

```sh
pylint xcp tests [optionally pass the flags or files to select which tests to run]
```

### Run all of the above on one go in defined virtual environments

```sh
tox -e py311-cov-check-lint-mdreport
```

This also checks code coverage and ends with a test report from the pytest run.
If you just run `tox` without arguments, in addition, the unit tests are run with
all installed Python versions (out of the list of 3.11, 3.12 and 3.13)

### Run pre-commit for all checks

To run all tests, including trailing whitespace checks, run

```sh
pre-commit run -av
```

## Alternative: installing pytest packages using `pipx`

`pipx` installs tools in `~/.local/share/pipx/venvs` which can be an alternate
way to install up-to-date python tools

```bash
python3.11 -m pip install pipx
pipx install tox; pipx install 'pytest<7';pipx install pylint pyright
pipx inject pytest pytest-{forked,localftpserver,pythonpath,subprocess,timeout} pyfakefs pytest_httpserver six mock
pipx inject pylint pyfakefs six mock pytest{,_forked,-localftpserver}
```

### Updating the documentation

For consistently well-spaced documentation, all Markdown files are checked
in CI using Markdownlint, which ensures that e.g. code blocks are separated
by space from the preceeding and following paragraphs and so on. This helps
to keep the Markdown source as well-readable as the rendered Markdown.

To check and fix Markdown files quickly, use:

```sh
pre-commit run -av markdownlint
```

### Removing trailing whitepace and fixing files to have only one trailing newline

These fixers detect and fix trailing whitespace and trailing newlines in files
to keep commits clean of adding trailing whitespace and are used in GitHub CI:

```sh
pre-commit run -av trailing-whitespace
pre-commit run -av end-of-file-fixer
```

## Background information on the provided tools

### Testing locally and in GitHub CI using `tox`

This project uses `tox` to run the tests for different python versions. Intro:

> _"Managing a Project's Virtual environments with `tox` -
> A comprehensive beginner's introduction to `tox`":_
> <https://www.seanh.cc/2018/09/01/tox-tutorial>

`tox` runs `pytest`, `pylint` and static analysis using `mypy`, `pytype`, and `pyright`.
Links:

- <https://mypy.readthedocs.io/en/stable>
- <https://microsoft.github.io/pyright>
- <https://google.github.io/pytype>

With `tox`, developers can run the full test suite for Python 2.7 and 3.x.
The same test suite is used in GitHub CI:

```bash
pip3 install --user --upgrade 'py>=1.11.0' 'virtualenv<20.22' 'tox==4.5.1'; hash -r; tox
```

Explanation:

- `tox>=4` is needed in order to fix reading the python2.7 dependencies from `pyproject.toml`
- `tox==4.5.1` is the last version not depending on `virtualenv>=20.23` (breaks Python 2.7)
- The latest versions of `tox` need `'py>=1.11.0'`. This ensures that it is at least `1.11`.
- `virtualenv-20.22` breaks using python2.7 for the `py27`, so has to be `virtualenv<20.22`.

## Installation of all development dependencies

Using pip-tools, you can extract the requirements and extras from `pyptoject.toml`:

```bash
PYTHON=python3.10
EXTRAS=.,test,mypy,pyright,pytype,tox
PFLAGS="--no-warn-conflicts"
$PYTHON -m pip install pip-tools==7.3.0
$PYTHON -m piptools compile --extra=$EXTRAS -o - pyproject.toml |
    $PYTHON -m pip install -r /dev/stdin $PFLAGS
```

With this, you can run most of the CI tests run by `tox` and GitHub CI also from the shell.

You can use e.g.: `tox -e py27-test -e py3.10-covcombine-check`
The syntax is `-e py<python-version>-<factor1>[-factor2]`.
A few of the factors are:

- `test`: runs `pytest`
- `cov`: runs `pytest --cov` and generates `XML` and `HTML` reports in `.tox/py<ver>-cov/logs/`
- `check`: runs `mypy`
- `fox`: runs like `cov` but then opens the `HTML` reports in Firefox

## Recommended `tox` and `pytest` plugins for development

When updating existing tests or developing new code with new test coverage, we might want to
ignore all other tests. This can be achieved with an exciting plugin called `pytest-picked`:
`pytest --picked` will collect all test modules that were newly created or changed but not
yet committed in a Git repository and run only them.

`pytest-sugar` is a plugin that, once installed, automatically changes the format of the
`pytest` standard output to include a graphical %-progress bar when running the test suite.

For nicer diffs of dictionaries, arrays and the like, use `pytest-clarity` or `pytest-icdiff`:

```py
pip install "pytest<7" pytest-picked pytest-sugar pytest-clarity # pytest-icdiff
```

To verify or extract the dependencies and extras configured in `pyproject.toml` and `tox.ini`
for specific `tox` environments, you can use
<https://pypi.org/project/tox-current-env>:

```bash
tox --print-deps-to=pytype-deps.txt --print-extras-to=pytype-extras.txt -e pytype
```

For more information to debug `pytest` test suites see
<https://stribny.name/blog/pytest>:

## Running GitHub actions locally using `act`

With `docker` (or `podman`) installed, [act](https://github.com/nektos/act) can be used to run
the CI jobs configured in [`.actrc`](https://github.com/xenserver/python-libs/blob/master/.actrc):

- `act` uses `docker` (also mimicked by `podman-docker`) to run GitHub actions locally
- While `act` does not use the same GitHub runner images, they are similar.

### `act` using `podman` with `podman-docker` instead of `docker`

This allows to use a user-local `podman` daemon in a `systemd ---user` session.
Thus, the containers and images are local to the development user.
With it, multiple users can use it on the same host without interfering with each other.
The `podman` daemon and all `pods` are completely unprivileged and rootless.

Fedora 37:

```bash
sudo dnf install podman-docker
# Note: If possible, don't install the act-cli.rpm because it is old and it
# needs different configuration, e.g. the unix:// prefix needs to be omitted!
```

Ubuntu 22.04:

```bash
sudo apt-get install -y podman-docker
```

Install `act` as `~/.local/bin/act`

```bash
curl -L https://github.com/nektos/act/releases/latest/download/act_Linux_x86_64.tar.gz|
    tar xfz - -C ~/.local/bin
```

To run `podman` as your user, run these as your user:

```bash
systemctl enable --now --user podman.socket # Only configures the podman socket
systemctl start --user podman.socket        # Start the docker-compatible unix socket
# Ubuntu only, Fedora 37 configures it already with more unqualifies search registries:
echo 'unqualified-search-registries = ["docker.io"]' | sudo tee -a /etc/containers/registries.conf
sudo touch /etc/containers/nodocker         # Quiet the docker emulation notification
echo "--container-daemon-socket unix://$XDG_RUNTIME_DIR/podman/podman.sock" >>~/.actrc
```

In any case, you should test the `docker` interface now:

```bash
docker run -it --rm alpine:latest grep NAME /etc/os-release
```

## Recommendations for Windows and WSL2

### Using Docker on WSL2/22.04

Ubuntu 22.04 LTS uses `iptables-nft` by default.
Switch to `iptables-legacy` so that Docker will work:
<https://crapts.org/2022/05/15/install-docker-in-wsl2-with-ubuntu-22-04-lts>

### Copy selection on selecting test (without need for Ctrl-C)

On traditional X11 and KDE Plasma, selected text is automatically copied
to the X selection/clipboard for pasting it. To use this engrained behavior
on Windows as well, it seems the only reliable way to have it for all apps
is a `AutoHotKey` script:

- <https://www.ilovefreesoftware.com/30/tutorial/auto-copy-selected-text-clipboard-windows-10.html>

While individual extensions for VS Code, Firefox, chrome do work partially,
they either don't cover the Firefox URL bar, the VS Code terminal and so on:

- <https://addons.mozilla.org/en-GB/firefox/addon/copy-on-select-2>
- <https://marketplace.visualstudio.com/items?itemName=dinhani.copy-on-select> (VS Code)
- <https://www.jackofalladmins.com/knowledge%20bombs/dev%20dungeon/windows-terminal-copy-selection/>
