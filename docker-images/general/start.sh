#! /usr/bin/env sh
set -e

# Try to find a minion application that can be started
# And add appropriate values to some environment variables
if [ -f app/app/minion.py ]; then
    DEFAULT_MODULE_NAME=app.minion
elif [ -f app/minion.py ]; then
    DEFAULT_MODULE_NAME=minion
fi
export MODULE_NAME=${MODULE_NAME:-$DEFAULT_MODULE_NAME}
export VARIABLE_NAME=${VARIABLE_NAME:-minion}
export PYTHONPATH=$PYTHONPATH:app

# If there's a prestart.sh script in the
# app directory or other path specified, run it before starting
PRE_START_PATH=${PRE_START_PATH:-app/prestart.sh}
echo "Checking for script in $PRE_START_PATH"
if [ -f $PRE_START_PATH ] ; then
    echo "Running script $PRE_START_PATH"
    . "$PRE_START_PATH"
else
    echo "There is no script $PRE_START_PATH"
fi

# if there's a virtual environment we going to activate it
# which makes installations of own packages possible and easier
if [ -d /home/minion/venv ] ; then
    echo "Activating virtual environment"
    . /home/minion/venv/bin/activate
fi

echo "Working directory: $(pwd)"
echo "Python Interpreter: $(which python3)"
echo "Module Name: ${MODULE_NAME}"
echo "Variable Name: ${VARIABLE_NAME}"
echo "Python Path: ${PYTHONPATH}"

# Nothing to start here
if [ "$#" -lt 1 ]; then
    exit 0
fi

# Try to infer whether a real script is given for startup or not
if [ -f "$1" ] && [ -x "$1" ] ; then
    # The command seems to be overriden, so we simply start using the given args.
    echo "Detected overriden startup options going to use them."
    exec "$@"
else
    # Seems like we have to startup a regular minion, so we try to use our start.py script
    echo "Use the integrated start.py script to startup a minion."
    exec python3 /home/minion/start.py "$@"
fi
