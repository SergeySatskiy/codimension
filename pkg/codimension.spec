%define version %{getenv:version}
%define requirements python, cdm-flowparser >= 1.0, cdm-pythonparser >= 2.0, PyQt4, qscintilla-python, pylint, python-pygments, python-chardet,  python-yapsy, pyflakes, python-rope, graphviz, pysvn

Name: codimension
Version: %{version}
Release: 2
License: GPLv3+
Group: Development/Tools/IDE
Summary: Python IDE with emphasis on graphical representation
BuildArch: noarch

Source0: %{name}-%{version}.tar.gz
Source1: %{name}.xpm
Source2: %{name}.sharedmimeinfo
Source3: %{name}.desktop
Source4: %{name}.png
Source5: %{name}-32x32.xpm

Requires: %{requirements}
BuildRequires: desktop-file-utils

%description
Codimension is an experimental Python IDE based on QT, QScintilla,
and a custom Python parser.

Features:

* Control flow diagram generation while the code is typed
* Hierarchical file/class/function/global variable browsers
* Docstrings as item tooltips in browsers
* Filtering in browsers
* Jump to a module import/symbol definition using a hot key
* See the list of symbol references
* Navigation history within a file and between files
* Syntax highlighting in the source code editor
* Pixmap viewer
* Skin support
* Diagram of imports for a file, directory, or the whole project
* Search in files
* Incremental search/replace in a file
* Search for a file/class/function/global variable in the project
* One-click intgration of external tools (pylint, pymetrics)
* Simple line counter
* McCabe cyclomatic complexity for a file or many files
* New file templates
* Pyflakes integration
* Python debugger

%prep
%setup -q -n %{name}-%{version}

%build

%install
mkdir -p $RPM_BUILD_ROOT/%{_datadir}
cp -pr src $RPM_BUILD_ROOT%{_datadir}/%{name}
cp -pr thirdparty $RPM_BUILD_ROOT%{_datadir}/%{name}/
cp -pr plugins $RPM_BUILD_ROOT%{_datadir}/%{name}-plugins
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
ln -s ../share/codimension/codimension.py $RPM_BUILD_ROOT/%{_bindir}/%{name}
mkdir -p $RPM_BUILD_ROOT%{_datadir}/pixmaps
cp -p %{SOURCE1} $RPM_BUILD_ROOT%{_datadir}/pixmaps/%{name}.xpm
cp -p %{SOURCE5} $RPM_BUILD_ROOT%{_datadir}/pixmaps/%{name}-32x32.xpm
cp -p %{SOURCE4} $RPM_BUILD_ROOT%{_datadir}/pixmaps/%{name}.png
mkdir -p $RPM_BUILD_ROOT%{_datadir}/mime/packages
cp -p %{SOURCE2} $RPM_BUILD_ROOT%{_datadir}/mime/packages/%{name}.xml
desktop-file-install --dir $RPM_BUILD_ROOT%{_datadir}/applications %{SOURCE3}

%post
update-mime-database %{_datadir}/mime
update-desktop-database -q

%postun
update-mime-database %{_datadir}/mime
update-desktop-database -q

%files
%defattr(-,root,root,-)
%{_bindir}/*
%{_datadir}/%{name}
%{_datadir}/%{name}-plugins
%{_datadir}/applications/*.desktop
%{_datadir}/mime/packages/*.xml
%{_datadir}/pixmaps/*.xpm
%{_datadir}/pixmaps/*.png

%changelog
* Tue May 06 2014 Ilya Loginov <isloginov@gmail.com> - 2.3.1-0
- New upstream release.

* Wed Mar 12 2014 Ilya Loginov <isloginov@gmail.com> - 2.3.0-0
- New upstream release.

* Fri Dec 27 2013 Ilya Loginov <isloginov@gmail.com> - 2.2.2-0
- New upstream release.

* Sat Dec 14 2013 Ilya Loginov <isloginov@gmail.com> - 2.2.1-0
- New upstream release.
- Add dependency from pysvn.

* Sat Nov 16 2013 Ilya Loginov <isloginov@gmail.com> - 2.2.0-2
- New upstream release.

* Fri Aug 23 2013 Ilya Loginov <isloginov@gmail.com> - 2.1.1-2
- New upstream release.

* Wed Aug 14 2013 Ilya Loginov <isloginov@gmail.com> - 2.1.0-2
- New upstream release.

* Sun Jun 30 2013 Ilya Loginov <isloginov@gmail.com> - 2.0.2-2
- New upstream release.

* Tue Jun 18 2013 Ilya Loginov <isloginov@gmail.com> - 2.0.1-1
- New upstream release.
- Replacing the 'file' utilities calls with magic module included in thirdparty
  directory.

* Wed Jun 05 2013 Ilya Loginov <isloginov@gmail.com> - 2.0-1
- New upstream release.

* Sun Jan 20 2013 Sergey Satskiy <sergey.satskiy@gmail.com> - 1.8-1
- New upstream release.

* Sun Oct 14 2012 Dmitry Kazimirov <dk@revl.org> - 1.7-1
- New upstream release.

* Mon Sep 17 2012 Dmitry Kazimirov <dk@revl.org> - 1.6-1
- New upstream release.

* Thu Jan 26 2012 Dmitry Kazimirov <dk@revl.org> - 1.4-1
- New upstream release.
- Dependency from the rope refactoring library is introduced.

* Thu Dec 15 2011 Dmitry Kazimirov <dk@revl.org> - 1.3-1
- New upstream release.

* Wed Oct 19 2011 Dmitry Kazimirov <dk@revl.org> - 1.2-1
- New upstream release.

* Tue Sep 13 2011 Dmitry Kazimirov <dk@revl.org> - 1.1-1
- New upstream release.

* Mon Sep 05 2011 Dmitry Kazimirov <dk@revl.org> - 1.0-1
- Initial release.
