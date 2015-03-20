setlocal

set PY_MAJ=2
if not "%1" == "" set PY_MAJ=%1
set PY_MIN=5
if not "%2" == "" set PY_MIN=%2

set PYTHONPATH=pyds%PY_MAJ%%PY_MIN%
c:\python%PY_MAJ%%PY_MIN%\python Demo\test_example.py

if exist pyds%PY_MAJ%%PY_MIN%\pycxx_iter.pyd c:\python%PY_MAJ%%PY_MIN%\python Demo\test_pycxx_iter.py
endlocal
