################################################################################
#
# PREAMBLE SECTION:
#		- contains information about the package, shown with rpm -qi
#
################################################################################
Summary: Tivoli Workload Scheduler for Applications 8.6.0
Name: twsapps86
Version: 8.6.0
Release: 2
License: Proprietary
Group: System Environment/Tools
Source: %{name}-%{version}.%{_target_cpu}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-root
Distribution: RHEL6
AutoReqProv: No
# BuildArch: i386 
# Due to unresolvable dependencies found by auto-find-requires we have to disable it here:
%define __find_requires %{nil}

Requires: /usr/lib64/libstdc++.so.5
Requires: tws92
Requires: saprfcsdk

Vendor: aaxc
Packager: Stefan Meyer (stefan@aaxc.net)

%description
Tivoli Workload Scheduler for Applications 8.6.0

%prep
# setup is not a section even due to leading %, it is a shell macro
%setup
###############################################################################
#
# BUILD STEP: 
################################################################################
%build

################################################################################
#
# INSTALL STEP: 
################################################################################
%install
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
# simply clean the BUILD ROOT again
rm -rf $RPM_BUILD_ROOT


################################################################################
# 
# THE FOLLOWING STEPS ARE DONE AT THE TARGET HOST (DURING RPM TRANSACTION)
#
################################################################################
################################################################################
#
# PRE STEP: 
#
################################################################################
%pre

################################################################################
#
# POST STEP: 
#
################################################################################
%post

# Installation des Produktes
/tmp/twsapps86/LINUX/INSTALLER/setup.sh -i silent -f /tmp/twsapps86/rspfile.txt
#if [ $? != 0 ]; then exit 1; fi

rm -rf /tmp/twsapps86

################################################################################
#
# PREUN STEP: 
#
################################################################################
%preun
echo "Uninstall would destroy the whole TWS installation. So i will just remove the entry from the rpm database..."
echo "Please clean up the mess yourself."

################################################################################
#
# POSTUN STEP: 
#
################################################################################
%postun
# TODO



################################################################################
#
# FILES SECTION:
#
################################################################################
%files -f FILES

%changelog
* Wed Apr 24 2013 Stefan Meyer (stefan@aaxc.net> 8.6.0-1
- Erstellung RPM, basierend auf TWS Apps 8.5.1 RPM
