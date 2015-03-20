setlocal
call setup-msvc90
c:\python27.win32\python setup_makefile.py win32 win32.mak
nmake -f win32.mak clean all 2>&1 | c:\unxutils\tee tmp-python27-build.log
nmake -f win32.mak test 2>&1 | c:\unxutils\tee tmp-python27-test.log

c:\python32.win32\python setup_makefile.py win32 win32.mak
nmake -f win32.mak clean all 2>&1 | c:\unxutils\tee tmp-python32-build.log
nmake -f win32.mak test 2>&1 | c:\unxutils\tee tmp-python32-test.log

c:\python33.win32\python setup_makefile.py win32 win32.mak
nmake -f win32.mak clean all 2>&1 | c:\unxutils\tee tmp-python33-build.log
nmake -f win32.mak test 2>&1 | c:\unxutils\tee tmp-python33-test.log

c:\python34.win32\python setup_makefile.py win32 win32.mak
nmake -f win32.mak clean all 2>&1 | c:\unxutils\tee tmp-python34-build.log
nmake -f win32.mak test 2>&1 | c:\unxutils\tee tmp-python34-test.log

endlocal
