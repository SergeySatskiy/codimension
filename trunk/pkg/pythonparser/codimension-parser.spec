Name: codimension-parser
Version: 1.5
Release: 2
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
* Sun Oct 14 2012 Dmitry Kazimirov <dk@revl.org> - 1.5-2
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
