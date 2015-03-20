#!/bin/bash
set -e
OS=${1:-macosx}

for PYTHON in \
    python2.6 \
    python2.7 \
    python3.2 \
    python3.3 \
    python3.4 \
    ;
do
    if which $PYTHON >/dev/null
    then
        ${PYTHON} setup_makefile.py ${OS} tmp-$PYTHON.mak
        make -f tmp-$PYTHON.mak clean 2>&1 | tee tmp-$PYTHON.log
        make -f tmp-$PYTHON.mak test 2>&1 | tee -a tmp-$PYTHON.log
    fi
done
