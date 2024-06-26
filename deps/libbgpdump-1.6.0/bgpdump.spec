Summary: MRT file reader
Name: libbgpdump
Version: 1.6.0
Release: 1
License: GPL
URL: http://www.ris.ripe.net/source/
Vendor: RIPE NCC Information Services department
Group: System Environment/Libraries
Source: libbgpdump-1.6.0.tgz
BuildRoot: /var/tmp/%{name}-root
BuildRequires: bzip2-devel zlib-devel

%description
This library reads MRT files as, amongst others, produced
by the RIPE NCC routing information service.

This library is maintained by the RIPE NCC Information
Services department: ris@ripe.net

%package devel
Summary: Libraries, includes to develop applications with %{name}.
Group: Development/Libraries
Requires: %{name} = %{version}

%description devel
The %{name}-devel package contains the header files and static libraries for
building applications which use %{name}.


%prep
%setup

%build
%configure
make CFLAGS="$RPM_OPT_FLAGS"

%install
rm -rf %{buildroot}
%makeinstall

%clean
rm -rf %{buildroot}

%files
%defattr(0755,root,root)
%{_bindir}/bgpdump
%defattr(-,root,root)
%{_libdir}/libbgpdump.a
%{_libdir}/libbgpdump.so

%files devel
%defattr(-,root,root)
%{_includedir}/bgpdump_attr.h
%{_includedir}/bgpdump_formats.h
%{_includedir}/bgpdump_lib.h
%{_includedir}/bgpdump_mstream.h

%changelog
* Wed Jul 04 2008 Erik Romijn <eromijn@ripe.net> 1.4.99.9-1
- Initial release
