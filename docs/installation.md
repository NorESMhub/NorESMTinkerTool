# Installation
!!! note
    Note that the package requires python >=3.10,<3.12.

## Setup the virtual environment.
```
python -m venv tinkertool && source tinkertool/bin/activate
```

## clone repository:
```
git clone https://github.com/NorESMhub/NorESMTinkerTool.git && cd NorESMTinkerTool
```

## Install

```
pip install  ./
```
Or, to include optionals:
```
pip install  .[optional1, ..., optional]
```
Available optionals:

* sampling
* plotting

!!! warning "Optionals"
    - If the `-e` flag is added, the package is installed in editable mode. If it is not included, changes to configuration files etc. will not be available until you re-install the package.
    - There are no spaces between optionals and the ',' character.


!!! note "Development"
    For development, [poetry](https://python-poetry.org/) is needed to install the documentation and development dependencies. 
    Once Poetry has been installed, development dependencies can be installed using:

    ```bash
    poetry install --with-all-groups
    ```
