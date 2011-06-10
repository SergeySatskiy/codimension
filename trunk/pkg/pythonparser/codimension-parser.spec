Name: codimension-parser
Version: 1.0
Release: 1%{?dist}
License: GPLv3+
Group: Development/Languages
Summary: Fast and comprehensive parser of the Python language
Source0: %{name}-%{version}.tar.gz

Requires: python2

BuildRequires: libtool
BuildRequires: python2-devel

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
* Fri Jun 10 2011 Dmitry Kazimirov <dk@revl.org> - 1.0-1
- Initial release.
