# !/bin/bash
export WHEELHOUSE=wheelhouse
export PIP_WHEEL_DIR=wheelhouse
export PIP_FIND_LINKS=wheelhouse

virtualenv -p python3 venv
. venv/bin/activate

pip wheel .[dev]
pip install --no-index -f wheelhouse flask_ussd_flow[dev]

coverage run -m pytest test 

deactivate
rm -rf venv
rm -rf wheelhouse