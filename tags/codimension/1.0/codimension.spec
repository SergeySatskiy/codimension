Name: codimension
Version: 1.0
Release: 1
License: GPLv3+
Group: Development/Tools/IDE
Summary: Python IDE with emphasis on graphical representation
BuildArch: noarch

Source0: %{name}-%{version}.tar.gz
Source1: %{name}.png
Source2: %{name}.sharedmimeinfo
Source3: %{name}.desktop

Requires: python2
Requires: codimension-parser >= 1.2
Requires: PyQt4 qscintilla-python
Requires: pylint python-chardet graphviz

BuildRequires: desktop-file-utils

%description
Codimension is an experimental Python IDE based on QT, QScintilla,
and a custom Python parser.

Features:

* Hierarchical file/class/function/global variable browsers
* Docstrings as item tooltips in browsers
* Filtering in browsers
* Jump to a module import/symbol definition using a hot key
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

%prep
%setup -q -n %{name}-%{version}

%build

%install
mkdir -p $RPM_BUILD_ROOT/%{_datadir}
cp -pr src $RPM_BUILD_ROOT%{_datadir}/%{name}
cp -pr thirdparty $RPM_BUILD_ROOT%{_datadir}/%{name}/
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
ln -s ../share/codimension/codimension.py $RPM_BUILD_ROOT/%{_bindir}/%{name}
mkdir -p $RPM_BUILD_ROOT%{_datadir}/pixmaps
cp -p %{SOURCE1} $RPM_BUILD_ROOT%{_datadir}/pixmaps/%{name}.png
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
%{_datadir}/applications/*.desktop
%{_datadir}/mime/packages/*.xml
%{_datadir}/pixmaps/*.png

%changelog
* Mon Sep 05 2011 Dmitry Kazimirov <dk@revl.org> - 1.0-1
- Initial release.
