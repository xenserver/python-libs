# Development setup

## Create a virtual environment with the test dependencies

```bash
python -m venv .venv
. .venv/bin/activate
pip install pip-tools==7.3.0
pip-compile --extra=test,mypy,pyright,pytype,tox -o - pyproject.toml | pip install -r /dev/stdin
```

## Development setup on Fedora 37

On Fedora 37, the `tox` rpm installs all Python versions.
But this `tox` is older, so install `tox==4.5.1` using `pip` (see below)

```bash
sudo dnf install tox;sudo rpm -e tox
```

But preferably use `tox` from the virtual environment instead.

## Development setup on Ubuntu 24.04

Prefer the virtual environment. Alternatively, an option is to use `pipx`:

```bash
sudo apt install pipx
pipx install tox; pipx install 'pytest<7';pipx install pylint
pipx inject pytest pytest-{forked,localftpserver,pythonpath,subprocess,timeout} pyfakefs pytest_httpserver six mock
pipx inject pylint pyfakefs six mock pytest{,_forked,-localftpserver}
```

Use the `deadsnakes` ppa to install Python versions like 3.8 and 3.11 (see below)

## Development setup on Ubuntu 22.04

Usage of <https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa> to install
other python versions.

```bash
sudo apt update
sudo apt install software-properties-common python{2,3}-dev
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get install -y python3.{8,11}{,-distutils}
```

Installation of additional python versions for testing different versions:

- If `deadsnakes/ppa` does not work, e.g. for Python 3.6, `conda` or `pyenv` can be used.
  For instructions, see <https://realpython.com/intro-to-pyenv>:

  ```bash
  sudo apt install -y build-essential xz-utils zlib1g-dev \
                      lib{bz2,ffi,lzma,readline,ssl,sqlite3}-dev
  curl https://pyenv.run | bash  # add displayed commands to .bashrc
  ~/.pyenv/bin/pyenv install 3.{6,8,11} && ~/.pyenv/bin/pyenv local 3.{6,8,11} # builds them
  ```

- For testing on newer Ubuntu which has `python2-dev`, but not `pip2`, install `pip2` this way:

  ```bash
  curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py;sudo python2 get-pip.py
  ```

You may want to install `pytype` in your user environment to run it directly without `tox`:

```bash
# On Python != 3.8, pytype can't import xml.dom.minidom, use 3.8:
python3.8 -m pip install pytype
python -m pip install tabulate
./pytype_runner.py
```

## Installation of dependencies using `pip`

### Testing locally and in GitHub CI using `tox`

This project uses `tox` to run the tests for different python versions. Intro:

> _"Managing a Project's Virtual environments with `tox` -
> A comprehensive beginner's introduction to `tox`":_
> <https://www.seanh.cc/2018/09/01/tox-tutorial>

`tox` runs `pytest`, `pylint` and static analysis using `mypy`, `pyre`, `pytype`, and `pyright`.
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
