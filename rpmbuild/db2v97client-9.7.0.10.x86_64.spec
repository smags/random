################################################################################
#
# PREAMBLE SECTION:
#		- contains information about the package, shown with rpm -qi
#
################################################################################
Summary: IBM DB2 Client v.9.7 FP10
Name: db2v97client
Version: 9.7.0.10
Release: 1
License: Proprietary
Group: System Environment/Tools
Source0: %{name}-%{version}.%{_target_cpu}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-root
Distribution: RHEL5
AutoReq: No
# BuildArch: i386 
%define __find_requires %{nil}
Provides: DB2Client
# Server und Client in derselben Version nicht parallel installieren! sme
Conflicts: db2v97
Vendor: aaxc
Packager: Stefan Meyer (stefan@aaxc.net)


%description
IBM DB2 Client 9.7.0.10

%prep

# setup is not a section even due to leading %, it is a shell macro
%setup

###############################################################################
#
# BUILD STEP: 
################################################################################
%build

# usually run 'configure' here, e.g.:
# ./configure CXXFLAGS=-O3 --prefix=$RPM_BUILD_ROOT/usr 
# usually run 'make' here

################################################################################
#
# INSTALL STEP: 
################################################################################
%install
# usually run 'make install' here
# - sets the umask
# - changes directory into the build area (default: %_topdir/BUILD) 
# - changes directory into subdir %{name}-%{version} 
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
# set -x


################################################################################
#
# POST STEP: 
#
################################################################################
%post
DB2_VERSION="9.7"

# Installation des Produktes
/tmp/db2v97client/db2_install -b /opt/db2/IBM/${DB2_VERSION}
if [ $? != 0 ]; then exit 1; fi

# Clientinstanz erstellen
echo "Erstelle DB2 Client Instanz..."
/opt/db2/IBM/${DB2_VERSION}/instance/db2icrt -s client ldb64cl
if [ $? != 0 ]; then exit 1; fi

# Setzen der Client Optionen
echo "Konfiguriere DB2 fuer LDAP..."
su - ldb64cl -c "/opt/db2/IBM/${DB2_VERSION}/adm/db2set DB2_ENABLE_LDAP=YES"
if [ $? != 0 ]; then exit 1; fi

su - ldb64cl -c "/opt/db2/IBM/${DB2_VERSION}/adm/db2set DB2LDAPCACHE=no"
if [ $? != 0 ]; then exit 1; fi

su - ldb64cl -c "/opt/db2/IBM/${DB2_VERSION}/adm/db2set DB2LDAPHOST=ldap.somehost.blah"
if [ $? != 0 ]; then exit 1; fi

su - ldb64cl -c "/opt/db2/IBM/${DB2_VERSION}/adm/db2set DB2LDAP_BASEDN=OU=DB2,DC=aaxci,DC=net"
if [ $? != 0 ]; then exit 1; fi

# Testen
#echo "Ausgabe der aktuellen DB2 Parameter (db2set):"
#su - ldb64cl -c "/opt/db2/IBM/${DB2_VERSION}/adm/db2set"

#clean tmp directory 
rm -rf /tmp/db2v97client

# ldconfig for libs
/sbin/ldconfig

#echo "Weiteres Vorgehen:"
#echo "Anzeigen der DB Liste mit /opt/db2/IBM/${DB2_VERSION}/bin/db2 list db directory"
#echo "Anzeigen aller LDAP DB2 Nodes mit /opt/db2/IBM/${DB2_VERSION}/bin/db2 list node directory"

# if [ $1 = 2 ]; then
# fi

################################################################################
#
# PREUN STEP: 
#
################################################################################
%preun
#echo "This ist PREUN..."
#set -x

################################################################################
#
# POSTUN STEP: 
#
################################################################################
%postun
#echo "This is POSTUN..."
#set -x
if [ $1 -eq 0 ]; then	# Nur ausfuehren wenn im UnInstall Mode
DB2_VERSION="9.7"

#echo "UnInstall Mode..."
# Client-Instanz loeschen
echo "Client Instanz loeschen..."
/opt/db2/IBM/${DB2_VERSION}/instance/db2idrop ldb64cl
  
# DB2 DeInstallieren (nur diese Version!)
echo "DB2 Client deinstallieren..."
/opt/db2/IBM/${DB2_VERSION}/install/db2_deinstall -a
  
### ldconfig for libs
/sbin/ldconfig

rm -rf /opt/db2/IBM/${DB2_VERSION}

fi


################################################################################
#
# FILES SECTION:
#
################################################################################
%files -f FILES

%changelog
* Thu Apr 14 2015 Stefan Meyer <stefan@aaxc.net> 9.7.0.10
- Sourcen upgedated auf IBM DB2 9.7 Client inklusive Fixpack 10
