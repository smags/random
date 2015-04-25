################################################################################
#
# PREAMBLE SECTION:
#		- contains information about the package, shown with rpm -qi
#
################################################################################
Summary: IBM DB2 v.10.5 FP3a
Name: db2v105
Version: 10.5.0.3
Release: 4
License: Proprietary
Group: System Environment/Tools
Source0: %{name}-%{version}.tar.gz
Source1: %{name}.conf
BuildRoot: %{_tmppath}/%{name}-%{version}-root
Distribution: RHEL5
AutoReqProv: No
Provides: DB2
Vendor: aaxc
Packager: Stefan Meyer (stefan@aaxc.net)

%description
IBM DB2 10.5.0.3a

%prep
# setup is not a section even due to leading %, it is a shell macro
%setup

###############################################################################
# BUILD STEP: 
################################################################################
%build
# usually run 'configure' here, e.g.:
# ./configure CXXFLAGS=-O3 --prefix=$RPM_BUILD_ROOT/usr 
# usually run 'make' here


################################################################################
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

install -d %{buildroot}/etc/ld.so.conf.d/
install -m644 %{SOURCE1} %{buildroot}/etc/ld.so.conf.d/

%clean
# simply clean the BUILD ROOT again
rm -rf $RPM_BUILD_ROOT
################################################################################
# 
# THE FOLLOWING STEPS ARE DONE AT THE TARGET HOST (DURING RPM TRANSACTION)
#
################################################################################


################################################################################
# PRE STEP: 
################################################################################
%pre
# set -x
if [ $1 -eq 2 ]; then
  echo "Update mode ist not supported..."
  exit 1
fi


################################################################################
# POST STEP: 
################################################################################
%post
# set -x
#### Start Variablen ####
RPM_NAME=DB2V105
DB2_VERSION="10.5"
#### Ende Variablen ####
 
if [ $1 = 1 ]; then
 # Installation des Produktes

  /tmp/db2v105/db2setup -r /tmp/db2v105/responsefile.rsp -l /tmp/db2setup.log
  if [ $? != 0 ]; then exit 1; fi

  # inittab sichern
  cp -f /etc/inittab /etc/inittab.${RPM_NAME}
  if [ $? != 0 ]; then exit 1; fi

  # Fault Monitor auf off setzen
  sed -i 's/fmc:2345:respawn/fmc:2345:off/g' /etc/inittab
  if [ $? != 0 ]; then exit 1; fi

  # inittab neu laden
  init q
  if [ $? != 0 ]; then exit 1; fi

  # DB2 Lizenzen installieren
  /opt/db2/IBM/${DB2_VERSION}/adm/db2licm -a /tmp/db2v105/db2/license/db2ese.lic
  if [ $? != 0 ]; then exit 1; fi
  /opt/db2/IBM/${DB2_VERSION}/adm/db2licm -a /tmp/db2v105/db2/license/db2aese_c.lic
  if [ $? != 0 ]; then exit 1; fi

  #clean tmp directory 
  rm -rf /tmp/db2v105

  # ldconfig for libs
  /sbin/ldconfig
fi

# Update
if [ $1 = 2 ]; then
  echo "Update mode ist not supported..."
  exit 1
fi


################################################################################
# PREUN STEP: 
################################################################################
%preun
# set -x
if [ $1 = 0 ]; then #first installation
fi

if [ $1 = 1 ]; then #update
fi


################################################################################
# POSTUN STEP: 
################################################################################
%postun
#### Start Variablen ####
RPM_NAME=DB2V105
DB2_VERSION="10.5"
#### Ende Variablen ####
if [ $1 = 0 ]; then #first installation

  # DB2 DeInstallieren (nur diese Version!)
  /opt/db2/IBM/${DB2_VERSION}/install/db2_deinstall -a
   if [ $? != 0 ]; then 
      echo "Error while the deinstallation. "
      exit 1
   fi
  ### ldconfig for libs
  /sbin/ldconfig
fi

if [ $1 = 1 ]; then #update
 echo "Update mode ist not supported..."
 exit 1
fi


################################################################################
# FILES SECTION:
################################################################################
%files -f FILES
# Note: At the buildhost we usually build as normal user, e.g rpmbuild. So we can't
# chown the files itself during rpmbuild. But we define the ownership the files will
# get later during INSTALLATION of the rpm because the installation (rpm -i) is done
# as root.
# Set the default attributes if no others are set at target host (using %attr)
# %defattr(-,root,root)
# For further information see also: 
# http://www.rpm-download-install.com/rpmguide/s1-rpm-inside-files-list-directives.html
/etc/ld.so.conf.d/*.conf
/tmp/db2v105/ibm_im/plugins/org.apache.ant_1.8.3.v20120321-1730/bin/runant.pyc
/tmp/db2v105/ibm_im/plugins/org.apache.ant_1.8.3.v20120321-1730/bin/runant.pyo

%changelog
* Tue Apr 22 2014 Stefan Meyer <stefan@aaxc.net> 10.5.0.3 
- build for x86
- initial version
