#!/bin/bash

set -x

source ~/virtualenv/python3.9/bin/activate

git pull

python --version

export DISPLAY=:99

# sudo systemctl start xvfb || exit 1
/usr/bin/Xvfb ${DISPLAY} -screen 0 1024x768x24 &
sleep 1
herbstluftwm &
sleep 1

PYTEST_ARGS=("-v")
PYTEST_ARGS+=("--cov=.")
PYTEST_ARGS+=("--log-file='${AFTER_FAILURE_LOGFILE:-logs/run_tests_log.txt}'")
PYTEST_ARGS+=("--log-format='%(asctime)s.%(msecs)03d %(module)-15s %(levelname)-8s %(threadName)-10s %(message)s'")
PYTEST_ARGS+=("--log-file-date-format='%H:%M:%S'")
PYTEST_ARGS+=("--log-level=DEBUG")

ulimit -c unlimited

if pytest "${PYTEST_ARGS[@]}"; then
  echo "Successful run"
else
  LOGFILE="${AFTER_FAILURE_LOGFILE:-logs/run_tests_log.txt}"
  if [ -f "${LOGFILE}" ]; then
    cat "${LOGFILE}"
  else
    echo "Logfile ${LOGFILE} not found"
  fi
fi

if [ -f core ]; then
  gdb python core
fi
