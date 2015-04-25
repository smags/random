Summary: Performance analysis tool
Name: nmon
Version: 14a
Release: 1
License: Proprietary
Group: Applications/System
Source0: %{name}-%{version}.tar.gz 
BuildRoot: %{_tmppath}/%{name}-%{version}-root

#ExclusiveArch: i386 x86_64 ppc ppc64

%description
nmon is designed for performance specialists to use for monitoring and
analyzing performance data.

%prep

%setup 

%build

%install
# clean the build root and recreate it
rm -rf $RPM_BUILD_ROOT
mkdir $RPM_BUILD_ROOT
# define what directories and files from sources are part of the rpm and should
# be copied into $RPM_BUILD_ROOT
cp -a * $RPM_BUILD_ROOT
# create dynamic file list
find . -type f > FILES  # all files
find . -type l >> FILES # all symbolic links
sed -i 's/^\.//g' FILES
# use globbing for file names with blanks
sed -i -e 's/^\([^ ]*\) .*$/\1*/g' FILES
# remove the temporary FILES file from file list
sed -i '/^.*\/FILES$/d' FILES
rm -f $RPM_BUILD_ROOT/FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f FILES
%defattr(-, root, root, 0755)
%defattr(-, nobody, nobody, 0755)

%changelog
* Tue Jan 27 2011 Stefan Meyer <stefan@aaxc.net> Version 1.0.0
- No comment


