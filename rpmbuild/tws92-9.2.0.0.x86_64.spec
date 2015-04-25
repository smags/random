################################################################################
#
# PREAMBLE SECTION:
#		- contains information about the package, shown with rpm -qi
#
################################################################################
Summary: Tivoli Workload Scheduler 9.2.0.0
Name: tws92
Version: 9.2.0.0
Release: 1
License: Proprietary
Group: System Environment/Tools
Source: %{name}-%{version}.%{_target_cpu}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}.%{_target_cpu}-root
Distribution: RHEL6
AutoReqProv: No
# BuildArch: i386 
# Due to unresolvable dependencies found by auto-find-requires we have to disable it here:
%define __find_requires %{nil}
Requires: /usr/lib64/libstdc++.so.5
Vendor: aaxc
Packager: Stefan Meyer (stefan@aaxc.net)

%description
Tivoli Workload Scheduler 9.2.0.0

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
# set -x

#### Start Variablen ####
USER_NAME=zcentric
USER_HOME=/opt/tws/zcentric/TWS
#### Ende Variablen ####


# User Verzeichnis(se) erstellen, verhindert das Dateien aus dem Skel kopiert werden
mkdir -p ${USER_HOME}
if [ $? != 0 ]; then exit 1; fi


################################################################################
#
# POST STEP: 
#
################################################################################
%post
# set -x
#### Start Variablen ####
CURRENT_DIR=`pwd`
USER_NAME=zcentric
USER_HOME=/opt/tws/zcentric/TWS
INSTALL_ROOT=/opt/tws/zcentric
#### Ende Variablen ####

# Installation des Produktes
/tmp/tws92/LINUX_X86_64/twsinst -new -uname ${USER_NAME} -addjruntime true -inst_dir ${INSTALL_ROOT}  -jmport 31114 -jmportssl false -skip_usercheck -acceptlicense yes
if [ $? != 0 ]; then exit 1; fi

# Nicht benoetigte Dateien loeschen
rm -f /opt/tws/zcentric/TWS/_uninstall/ACTIONTOOLS/CheckPrerequisites/DB2CHECKPREREQ/db2/solaris_x64/bin/db2prereqcheck

# Initskripte aktivieren
chkconfig tebctl-tws_cpa_agent_zcentric on
if [ $? != 0 ]; then exit 1; fi

rm -rf /tmp/tws86

################################################################################
#
# PREUN STEP: 
#
################################################################################
%preun
# TWS stoppen
echo "TWS wird gestoppt..."
service tebctl-tws_cpa_agent_zcentric stop

################################################################################
#
# POSTUN STEP: 
#
################################################################################
%postun
USER_NAME=zcentric

# Initskripte deaktivieren
/sbin/chkconfig --del tebctl-tws_cpa_agent_zcentric

# aufraeumen
rm -f /etc/init.d/tebctl-tws_cpa_agent_zcentric
rm -rf /opt/tws/zcentric
rm -rf /etc/TWS
rm -rf /root/.swdis

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
# %defattr(-,root,root)
# For further information see also: 
# http://www.rpm-download-install.com/rpmguide/s1-rpm-inside-files-list-directives.html

%changelog
* Wed Nov 05 2014 Stefan Meyer (stefan@aaxc.net> 9.2.0.0-1
- Erstellung RPM, basierend auf TWS 9.2.0.0
