Name: codimension-parser
Version: 1.6.4
Release: 1
License: GPLv3+
Group: Development/Languages
Summary: Fast and comprehensive parser of the Python language
Source0: %{name}-%{version}.tar.gz

Requires: python

BuildRequires: libtool
BuildRequires: python-devel

# Exclude .so libraries from the "Provides" list.
%{?filter_setup:
%filter_provides_in %{python_sitearch}/.*\.so$
%filter_setup
}

%description
Written as a part of the Codimension project, this parser aims at
pulling the most data from Python sources while exceeding the
speed of existing parsers.

%prep
%setup -q -n %{name}-%{version}

%build
%configure
make %{?_smp_mflags}

%install
make install DESTDIR=$RPM_BUILD_ROOT INSTALL="install -p"
find $RPM_BUILD_ROOT -name "*.la" -exec rm -f {} ';'

%files
%defattr(-,root,root,-)
%{python_sitearch}/*.so
%{python_sitearch}/*.py*
%{python_sitearch}/*.egg-info

%changelog
* Sat Nov 16 2013 Sergey Satskiy <sergey.satskiy@gmail.com> - 1.6.4-1
- Bug fix: core dump in case if a docstring is longer than 65535 bytes.
- Collect python files list from sys.path.

* Thu Aug 29 2013 Sergey Satskiy <sergey.satskiy@gmail.com> - 1.6.3-1
- Prepared for release v.1.6.3
- Bug fix: core dump in case of import without anything following it

* Sun Jun 30 2013 Sergey Satskiy <sergey.satskiy@gmail.com> - 1.6.2-1
- Prepared for release v.1.6.2
- Bug fix: parser was not able to parse python 3 style print() functions

* Tue Jun 18 2013 Sergey Satskiy <sergey.satskiy@gmail.com> - 1.6.1-2
- Bug fix: parser did not report errors if didn't reach the end
- Increased performance due to fixed size arrays
- Regexp based coding search is replaced with string search to avoid problems
  on cygwin and eliminate dependency on windows.

* Fri Jan 18 2013 Sergey Satskiy <sergey.satskiy@gmail.com> - 1.6-1
- Fix: docstrings comprised of many string literal parts are properly
  recognized.
- Fix: module docstring is recognized even if it is the only file content.
- Minor code cleanups targeting the parser performance.

* Wed Oct 31 2012 Dmitry Kazimirov <dk@revl.org> - 1.5-2
- Python dependency: python2 -> python

* Tue Sep 11 2012 Dmitry Kazimirov <dk@revl.org> - 1.5-1
- New: input stream offsets for most of the items.
- Fix to make the absPosition attribute accessible.

* Mon May 21 2012 Dmitry Kazimirov <dk@revl.org> - 1.4-1
- Upstream changes: Bug fix: make parseable the input where
  the last line is a comment and has no EOL.

* Tue Sep 13 2011 Dmitry Kazimirov <dk@revl.org> - 1.3-1
- Source line numbers and column positions are now remembered for
  class and function definitions.

* Fri Sep 02 2011 Dmitry Kazimirov <dk@revl.org> - 1.2-1
- Latest grammar fixes.
- Lexer errors are collected now too.
- First public release.

* Wed Jul 27 2011 Dmitry Kazimirov <dk@revl.org> - 1.1-1
- Added a new method 'getDisplayName' to parser classes 'ImportWhat',
  'Import', 'Decorator', 'Function', and 'Class'.

* Fri Jun 10 2011 Dmitry Kazimirov <dk@revl.org> - 1.0-1
- Initial release.
