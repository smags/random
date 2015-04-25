################################################################################
#
# PREAMBLE SECTION:
#		- contains information about the package, shown with rpm -qi
#
################################################################################
Summary: dbfacephp Reporting WebUI  
Name: dbfacephp
Version: 1.0.0
Release: 1
License: Proprietary
Group: 
Source0: %{name}-%{version}.%{_target_cpu}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}.%{_target_cpu}-root
Distribution: RHEL6
#AutoReq: No
AutoReqProv: No
# BuildArch: i386 
# Due to unresolvable dependencies found by auto-find-requires we have to disable it here:
%define __find_requires %{nil}
# Note: this is a dirty hack, yum has to parse the complete filelists, but it works
# Requires: compat-libstdc++-33.x86_64 # does not work, see also:
Requires: httpd, php54-php-pdo, php54-php-odbc, php54-php-pear, php54-php, php54-php-pgsql

# http://www.rpm.org/wiki/PackagerDocs/ArchDependencies
# Requires: compat-libstdc++-33%{?_isa} # seems to not work with rpm v- 4.4.2
# Provides: DB2
# Conflicts: mytestconflict
Vendor: aaxc
Packager: Stefan Meyer (stefan@aaxc.net)


%description
dbfacephp Reporting WebUI 1.0.0


%prep
# setup is not a section even due to leading %, it is a shell macro
%setup -n "%{name}-%{version}.%{_target_cpu}"
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
# if [ $1 -eq 1 ]; then
# first install
# fi

# if [ $1 -eq 2 ]; then
# update
# fi


################################################################################
#
# POST STEP: 
#
################################################################################
%post
# if [ $1 -eq 1 ]; then
# first install
# fi

# if [ $1 -eq 2 ]; then
# update
# fi

chown -R apache.apache /var/www/html/reports
chmod -R 755 /var/www/html/reports


################################################################################
#
# PREUN STEP: 
#
################################################################################
%preun
# if [ $1 -eq 1 ]; then
# Upgrade installation
# fi

# if [ $1 -eq 0 ]; then
# Initial installation
# fi


################################################################################
#
# POSTUN STEP: 
#
################################################################################
%postun
# if [ $1 -eq 1 ]; then
# Upgrade installation
# fi

# if [ $1 -eq 0 ]; then
# Initial installation
# fi


################################################################################
#
# FILES SECTION:
#
################################################################################
%files -f FILES
# Note: At the buildhost we usually build as normal user, e.g rpmbuild. So we can't
# chown the files itself during rpmbuild. But we define the ownership the files will
# get later during INSTALLATION of the rpm because the installation (rpm -i) is done
# as root.
# Set the default attributes if no others are set at target host (using %attr)
%defattr(-,root,root)
# For further information see also: 
# http://www.rpm-download-install.com/rpmguide/s1-rpm-inside-files-list-directives.html

# do not override the database
%config /var/www/html/reports/config/dbface.db

%changelog
* Thu Mar 10 2015 Stefan Meyer <stefan@aaxc.net> 1.0.0-1
- initial version

