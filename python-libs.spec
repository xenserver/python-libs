%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Common XenServer Python classes
Name: python-libs
Version: %{version}
Release: %{release}
Source: %{name}-%{version}.tar.gz
License: GPL
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
 
BuildRequires: python-devel python-setuptools

%description
Common XenServer Python classes.

%prep
%setup -q

%build
ls %{dirname}
%{__python} %{dirname}/setup.py build
 
%install
rm -rf $RPM_BUILD_ROOT
%{__python} %{dirname}/setup.py install -O1 --skip-build --root %{buildroot}
 
%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%{python_sitelib}


%changelog
