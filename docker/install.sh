#!/bin/bash

source ~/virtualenv/python3.9/bin/activate

python --version

pip install --upgrade pip
echo "Req File':' ${REQUIREMENTS:=requirements.txt}"
echo "Dev Req File':' ${DEV_REQUIREMENTS:=dev-requirements.txt}"
echo "Pip packages installed for CI':' ${PIP_CI_PACKAGES:=pytest-cov}"

# Install requirements
if [[ ! -f "${REQUIREMENTS}" ]]; then
    echo "File not found: ${REQUIREMENTS}" 1>&2
    travis_terminate 1
else
    pip install --requirement "${REQUIREMENTS}"
fi

# Install development requirements
if [[ ! -f "${DEV_REQUIREMENTS}" ]]; then
    echo "File not found: ${DEV_REQUIREMENTS}" 1>&2
    travis_terminate 1
else
    pip install --requirement "${DEV_REQUIREMENTS}"
fi

# Install Extras such as PyQt5
if [[ ! -z "${PIP_EXTRAS}" ]]; then
    echo "Installing extra pip dependencies."
    pip install ${PIP_EXTRAS}
fi

# Install Extras such as PyQt5
if [[ ! -z "${PIP_CI_PACKAGES}" ]]; then
    echo "Installing pip dependencies for CI."
    pip install ${PIP_CI_PACKAGES}
fi
