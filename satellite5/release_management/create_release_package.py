#!/usr/bin/env python

"""
This script creates different kinds of release rpms by the installed package
list of a system. Actually we support the following 3 types of a release
(unit):

 - Type OS:
   - The operating system sw stack of a default system (Core Build)
   - divides between i[36]86, i[36]86-PAE, x86_64 OS stack
   - including the software from all subscribed Red Hat sw chans
     (or their clones)
   - including the corp wide stage chan (generic sw chan for all systems)
   - usually created at a fresh installed system without defining 
     an application type
   - automatically sets actual running kernel as default kernel inside %post

 - Type System:
   - The complete sw stack of a system (type), e.g. CSC Webserver
   - includes all packages from all subscribed software chans installed
   - could be created everytime
   - automatically sets actual running kernel as default kernel inside %post

 - Type SW Stack:
   - The packages defined for a specified software stack (e.g. CSC Webserver)
   - including all packages from the sw stack specific child chan
   - including the dependencies (also from all other subscribed chans)
   - excluding all packages already defined in the OS release rpm
"""

import xmlrpclib
import sys
import getpass
import commands
import re
import os
import time
import csv
from xmlrpclib import DateTime
from time import time as Time
import ConfigParser
from optparse import OptionParser

########################################################################
#
# Customer-specific Options
#
########################################################################

DEFAULT_SATELLITE_HOST = "localhost"

########################################################################
#
# Misc. Settings
#
########################################################################

specfiledir = "/home/rpmbuild/SPECS"
currentDate = time.strftime("%Y%m%d")

########################################################################
#
# SCRIPT OPTIONS
#
########################################################################

scriptparser = OptionParser()

scriptparser.add_option("-H", "--server", dest="satelliteHost",
                        help="Satellite hostname")

scriptparser.add_option("-S", "--stack", dest="sw_stack", 
                        help="Software stack of the release package. Could be 'system', 'os' or a sw stack, e.g. 'csc-web'")

scriptparser.add_option("-s", "--system", dest="systemName", 
                        help="Regular expression to match the name of the system we should read the package list from.")

scriptparser.add_option("-r", "--releaseid", dest="releaseid", 
                        help="The releaseid we should use instead of the actual date.")

# TODO implement errata functionality
#scriptparser.add_option("-E", "--errata", dest="errata", 
#                        help="Create also an errata if param supplied.", 
#                        default=False, action="store_true")

scriptparser.add_option("-e", "--exclude", dest="exclude", 
                        help="Filename of exclude list file.")

scriptparser.add_option("-i", "--include", dest="include", 
                        help="Filename of include list file.")

scriptparser.add_option("-v", "--verbose", dest="verbose", 
                        help="Enable debugging output", 
                        default=False, action="store_true")

scriptparser.add_option("-x", "--exthelp", dest="exthelp", 
                        help="Extended help", 
                        default=False, action="store_true")

# TODO add an option --edit to offer the possibility to edit the created
# specfile on the fly

# parse command line options
(options, args) = scriptparser.parse_args()
if options.sw_stack:
   sw_stack = str.lower(options.sw_stack)

if options.exthelp:
   print __doc__
   sys.exit(0)

if not options.sw_stack:
   print "No software stack supplied. Please add option '-S <system|os|sthg_else>'"
   sys.exit(1)

# The script must be able to run without the /etc/sysconfig/rhof
# configuration file. In that case, set some default values and ask the user
# for the other settings.

if os.access("/etc/sysconfig/rhof", os.R_OK):
   parser = ConfigParser.SafeConfigParser()
   parser.readfp(open("/etc/sysconfig/rhof", "r"))

   SATELLITE_HOST = parser.get("rhof", "rhns_server")
   SATELLITE_LOGIN = parser.get("rhof", "rhns_user")
   SATELLITE_PASSWORD = parser.get("rhof", "rhns_password")
   SW_PREFIX = parser.get("config", "prefix_sw")
   STAGE1_NAME = parser.get("config", "stage1")

   WHITELIST_FILENAME = parser.get("config", "rel_whitelist")
   BLACKLIST_FILENAME = parser.get("config", "rel_blacklist")
else:
   if options.satelliteHost:
      SATELLITE_HOST = options.satelliteHost
   else:
      SATELLITE_HOST = DEFAULT_SATELLITE_HOST
   SW_PREFIX = "Custom"
   STAGE1_NAME = "Test"

   print "Satellite User: ",
   SATELLITE_LOGIN = sys.stdin.readline()
   SATELLITE_PASSWORD = getpass.getpass("Password: ")

   WHITELIST_FILENAME = "./release_rpm_whitelist"
   BLACKLIST_FILENAME = "./release_rpm_blacklist"

SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST
SW_PREFIX_LABEL = str.lower(SW_PREFIX)
STAGE1_LABEL = str.lower(STAGE1_NAME)

########################################################################
#
# CHECK REQUIREMENTS
#
########################################################################
# check if we have a filename for remote script, only exeption is --report

########################################################################
#
# HELPER FUNCTIONS
#
########################################################################
def gen_releaseid():
   """
   This function creates a release id. Actually we simply use the date
   including hour and minute. Later it is planned to use a generic release
   id which is stored in the CMDB / CMS.
   """

   releaseid = currentDate
   return releaseid

def create_release_rpm(systemId, sw_stack, release_id):
   """
   This function get the actual package list of a system sorted by
   channels. Only software channels related to the software stack given as
   the second param are relevant. This package list plus the packages from
   the whitelist minus the packages from the blacklist are used as requires
   for the release rpm. The function creates a specfile and build a rpm from
   it, signs it, pushs it into the release rpm software channel and adds
   this release to the releases overview page.
   """
   systemId = int(systemId)

   print "\nNote: Please run 'rhn-profile-sync; rhn_check' on system " + str(systemId)
   print "before running this script to update the package profile.\n"

   # we need the basechan information for arch and if stack = OS for label
   basechan = client.system.getSubscribedBaseChannel(key, int(systemId))
   system_arch = basechan['arch_name']
   basechanLabel = basechan['label']

   if system_arch == "IA-32":
      # Note: we set this to i686 because kernel is i686
      system_arch = "i686"

   all_sw_chans = [basechanLabel]

   # get a list of all existing software chans to check if channel exists 
   swchanlist = []
   swchannellist = client.channel.listAllChannels(key)
   for swchan in swchannellist:
      swchanlist.append(swchan['label'])
   
   print "Creating %s release RPM with release_id %s based on system %s" % \
       (sw_stack, release_id, systemId)

   # if the sw_stack == OS (operating system) we have to take all original
   # Red Hat Software Channels
   if str.lower(sw_stack) == "os":
      # this is the core operating system, this includes the generic corp
      # wide chan for this stage or with other words: it does NOT include
      # the sw stack related software chans
      regexp = '^(clone-\w+-)?rh|' + SW_PREFIX_LABEL + \
          '-stage-|' + SW_PREFIX_LABEL + '-' + STAGE1_LABEL + '-corp-'
      #regexp = '.*'
      #
      # custom-release-os-clone-prod-rhel-x86_64-server-5-5.5.0-1.x86_64.rpm
      #
   elif str.lower(sw_stack) == "system":
      # if we want to create a release rpm for a (type of) system we include
      # all chans and packages
      regexp = '.*'
   else:
      # if we look at a sw stack we have to find the channel with the
      # complete name between 2 minus

      # NOTE: we have also discussed the possibility to add also the deps of
      # the sw stack packages which usually come from the other (e.g. orig
      # RH channels) here (wider area). But this would lead to conflicting
      # packages with a different version of os release rpm. Following this
      # wider approach we would have to get *all* packages and then
      # substract the packages from the os release.

      # To reduce the release exactly to the packages come from the sw stack
      # responsible developers we now take only the packages coming from the
      # sw stack specific child channel. This leads to a gap of packages
      # installed which are not mentioned (neither in the os-release nor in
      # the sw-stack-release rpm).

      # changed: dherrman, 20100812: We now use all channels to get also
      # deps of software stack. To avoid overlapping requires between os
      # release and app stack release we now define that there must be a os
      # release rpm installed. So the requires of app stack are all
      # installed packages minus the packages already defined in the
      # (installed) os release rpm.

      # old approach, only app specific chan
      # regexp = '^' + SW_PREFIX_LABEL + '-type-' + sw_stack + '-.*$'  

      regexp = '.*'

   # get all subscribed software channels of this system
   all_childs = client.system.listSubscribedChildChannels(key, int(systemId))

   # iterate through all subscribed sw chans and get the chan we are
   # interested in (using the regexp)
   app_stack = None
   for child in all_childs:
      if re.match(regexp, child['label']):
         if options.verbose:
            print "Regexp %s matches at channel %s. Adding chan to chan list." % (regexp, child['label'])

         # add the chan label to array
         all_sw_chans.append(child['label'])

         # special use case: if we create a system release rpm we have to
         # find out the app type
         # TODO check if we can use the CIF (should be there at this time)
         # NOTE: Actually we assume that there is only ONE app type sw chan subscribed
         # TODO make this multi sw_stack aware
         reg = '^' + SW_PREFIX_LABEL + '-type-'
         if re.match(reg, child['label']):
            match = re.match('^' + SW_PREFIX_LABEL + '-type-(\w+-\w+)-', child['label'])
            app_stack = match.group(1)
      elif options.verbose:
         print "Regexp %s does NOT match at channel %s. Skipping chan." % (regexp, child['label'])

   # get the running kernel for PAE or not and for rpm post section (make
   # this kernel as default)
   try:
      runningkernel = client.system.getRunningKernel(key, systemId)
      if options.verbose:
         print "Got running kernel vom RHNS API: " + runningkernel
   except:
      print "\nERROR: Could not get the actual running kernel from system: " + str(systemId) + "\n"
   
   # calculate the specfile meta fields
   if str.lower(sw_stack) == "system":
      # Shorten the system name by removing everything after the first dot.
      systemName = client.system.getDetails(key, systemId)['profile_name']
      shortSystemName = re.split('\.', systemName, 1)[0]

      if app_stack is None:
         release_name = SW_PREFIX_LABEL + "-release-system-" + shortSystemName
      else:
         release_name = SW_PREFIX_LABEL + "-release-system-" + shortSystemName + \
             '-' + app_stack
   elif str.lower(sw_stack) == "os":
      if re.search('^.*PAE', runningkernel):
         release_name = SW_PREFIX_LABEL + "-release-os-" + basechanLabel + "-PAE"
         #release_name = SW_PREFIX_LABEL + "-release-os-" + "-PAE"
      else:
         release_name = SW_PREFIX_LABEL + "-release-os-" + basechanLabel
         #release_name = SW_PREFIX_LABEL + "-release-os-" 
   else:
      release_name = SW_PREFIX_LABEL + "-release-" + sw_stack 
      # since we now have to find the OS release RPM we have to calculate
      # the name of it even if we not create it now.
      if re.search('^.*PAE', runningkernel):
         os_release_name = SW_PREFIX_LABEL + "-release-" + sw_stack + \
             "-PAE"
      else:
         os_release_name = SW_PREFIX_LABEL + "-release-" + sw_stack

   if re.search('^.*PAE', runningkernel):
      runningkernelrpm = "kernel-PAE-" + re.split('PAE', runningkernel)[0]
   else:
      runningkernelrpm = "kernel-" + runningkernel

   # define some global values
   release_version = str(release_id) 
   specfilepath = specfiledir + "/" + release_name + "-" + release_version + \
       ".spec"

   # open file handle of specfile
   specfile = open(specfilepath, "w")
   rpmheader  = "# This RPM was automatically created using the release_package script.\n"
   rpmheader += "# Do not change the values below.\n"
   rpmheader += "Name: " + release_name + "\n"
   rpmheader += "Version: " + release_version + "\n"
   # TODO check if this release already exists and increment the value if yes
   rpmheader += "Release: 1" + "\n"
   rpmheader += "License: GPL" + "\n"
   rpmheader += "Group: System Environment/Base" + "\n"
   # TODO check if we really want to use BuildArch: what should we do at a
   # iX86 buildhost / RHNS server?
   # Note: For OS release we need the arch because the package set is
   # different between iX86 and x86_64 systems!
   rpmheader += "BuildArch: " + system_arch + "\n"
   rpmheader += "Summary: " + sw_stack + " release built at " + time.strftime("%d.%m.%Y %H:%M") + " for system " + str(systemId) + " by user " + SATELLITE_LOGIN + "\n"

   # write the spec file headers
   specfile.write(rpmheader)

   if options.verbose:
      print "We are searching for packages inside the following channels: ", all_sw_chans

   # parse the exclude file
   excludes = parse_excludes()

   # if this is a app stack release rpm we have to ignore the packages
   # already defined inside OS release rpm. The requirement is that the OS
   # release is already installed, so let's check this and store the
   # requires of it in an ignore list.
   if  str.lower(sw_stack) != "os" and str.lower(sw_stack) != "system":
      # check if OS release rpm is installed
      if options.verbose:
         print "Check if OS release rpm " + release_name + "-" + release_version + "-1 is installed at system " + str(systemId)
      try:
         # the naming convention is defined below during rpm meta header
         # creation. Please change it here too if you ever change this
         # below. See Concatenation of string 'os_release_name' above.
         
         # Note: Actually we have hardcoded release=1 here and inside RPM
         # meta header creation!
         client.system.isNvreInstalled(key, systemId, os_release_name, release_version, 1)
         print "OS RPM seems to be installed."
      except:
         # the OS release rpm is not installed. we can't proceed here.
         print "ERROR: No OS release rpm installed. Please install it and try it again."
         sys.exit(1)
   # else:
      # print "BLLAAA"

   # define the separator between name and version,release,epoch depending
   # on hard or soft lock used
   lock_sep = " = "

   # get the actual package list of this system
   for c in all_sw_chans:
      installedPackages = client.system.listPackagesFromChannel(key, systemId, c)

      for p in installedPackages:
         # check if package is at package blacklist
         if p['name'] in excludes:
            print "Package " + p['name'] + " skipped due to blacklist."
         else:
            if p['name'] == 'kernel':
               requires = 'Requires: kernel-' + system_arch
            else:
               requires = 'Requires: ' + p['name']

            requires += ' = '

            if p['epoch'] != '':
               requires += p['epoch'] + ':'

            requires += p['version'] + '-' + p['release']
            specfile.write(requires + '\n')

            # "Requires: foo = 1.2" allows an upgrade of the 64 bit package,
            # as long as the 32 bit package remains with version 1.2. To
            # prevent newer versions from being installed, we add a
            # Conflicts line.
            #
            # There may be multiple versions of the kernel package
            # installed, so we cannot include Conflicts for kernel
            # packages. This is OK because we don't have both 32 and 64 bit
            # versions of the kernel for one system.

            if not re.search('^kernel', p['name']):
               conflicts = 'Conflicts: ' + p['name'] + ' > '
               if p['epoch'] != '':
                  conflicts += p['epoch'] + ':'
               conflicts += p['version'] + '-' + p['release']
               specfile.write(conflicts + '\n')

   # add the packages from the package whitelist
   includes = parse_includes()
   if options.verbose:
      print "Adding packages from package whitelist: ", includes

   if len(includes) > 0:
      specfile.write("\n# Added from whitelist:\n")

      for package in includes:
         # TODO search this package via API and check if exists in the
         # subscribed channels.
         if options.verbose:
            print "TODO: Checking if package exists: " + package

         # Convert the space-separated name,version,release format to an
         # RPM Requires line.
         pack = package.split(' ')
         if len(pack) == 3:
            specfile.write("Requires : " + pack[0] + " = " + pack[1] + "-" +
                           pack[2] + "\n")
         elif len(pack) == 2:
            specfile.write("Requires : " + pack[0] + " = " + pack[1] + "\n")
         else:
            specfile.write("Requires : " + pack[0] + "\n")

   # Even though the RPM does not contain anything, we need the sections for
   # building it.
   rpmsections  = "\n\n%description\n"
   rpmsections += "Release RPM for software stack " + sw_stack + \
       " generated at " + currentDate + "\n"
   rpmsections += "Release version: " + release_version + "\n"
   rpmsections += "This meta RPM describes the release tested in QA stage.\n\n"
   rpmsections += "\n\n%prep\n\n%build\n\n%install\n\n%clean\nrm -rf $RPM_BUILD_ROOT\n\n%files\n\n"

   # sw_stack=os|system: post section and set running actual kernel as default kernel at the target system
   if str.lower(sw_stack) == "os" or str.lower(sw_stack) == "system": 
      rpmsections += '# Post Section\n%post\n'
      rpmsections += '# Setting the running kernel of Test / QA system to default one\n'
      rpmsections += 'export kernel_path=$(rpm -ql ' + runningkernelrpm + ' | grep /boot/vmlinuz)\n'
      rpmsections += '/sbin/grubby --set-default=${kernel_path}\n'

   specfile.write(rpmsections)
   specfile.close()

   # Open SPEC File in VIM to add some more information manually
   os.system('vim ' + specfilepath) 

   # build the rpm now
   print "Building RPM with spec file " + specfilepath + "\n"
   # TODO check if we use --sign to automate the push at the end
   rpmbuildcmd = "setarch " + system_arch + " rpmbuild -bb " + specfilepath + ' 2>&1 | grep -e "^Wrote: " -e "^Erstellt: "'

   #out = os.system(rpmbuildcmd)
   out = commands.getoutput(rpmbuildcmd)	
   
   if re.search('(Wrote:\s|Erstellt:\s).*\.rpm', out):
      # if we found the string the package has been built
      m = re.search('(Wrote:\s|Erstellt:\s)(.*.rpm)', out)
      final_package = m.groups()[1]
      print "Successfully built the release RPM:\n" + final_package
   else:
      sys.stderr.write("Building the RPM from specfile " + specfilepath + " failed\n")
      sys.stderr.write(out + "\n")
      sys.exit(1)

   # TODO push the rpm into the right channel
   # the channel is either the software chan of this sw_stack the corp wide
   # sw_chan of STAGE1
   if str.lower(sw_stack) == "os":
      # due to naming convention every stage has its own corp wide chan we
      # use this script inside stage 1 (Dev) and so we need to push it into
      # the corp wide chan of this stage
      # ex for a corp wide chan: rinn-stage-ref-rhel-i386-server-5 
      channel2push = SW_PREFIX_LABEL + '-stage-' + STAGE1_LABEL + \
          '-' + basechanLabel
   elif str.lower(sw_stack) == "system":
      # this is a system release, but every system must have an application
      # type. So we will upload the package into the software chan of the
      # application type.
      if app_stack is None:
         channel2push = SW_PREFIX_LABEL + '-' + STAGE1_LABEL + \
             '-corp-' + basechanLabel
      else:
         channel2push = SW_PREFIX_LABEL + '-type-' + app_stack + '-' + \
             STAGE1_LABEL + '-' + system_arch
   else:
      # due to naming convention every sw_stack has its own sw chan
      # we use this script inside STAGE1 (QA) and so we need to push it into
      # the sw chan of this stage
      # ex for a sw_stack chan of STAGE1: rinn-type-acsc-app-ref-rhel-i386-server-5 
      channel2push = SW_PREFIX_LABEL + '-type-' + sw_stack + '-' + \
          STAGE1_LABEL + '-' + system_arch


########################################################################
#
# RHN SATELLITE LOGIN
#
########################################################################

def connect2rhns():
   # RHN Satellite Login and get session key
   if options.verbose:
      print "Connecting to %s with login %s" % (SATELLITE_URL, SATELLITE_LOGIN)
   try:
      global client
      global key
      client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
      key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)
   except:
      sys.stderr.write("ERROR: Could not connect to %s with login %s\n" %
                       (SATELLITE_URL, SATELLITE_LOGIN))
      sys.exit(1)

########################################################################
#
# PARSE EX/INCLUDE FILE AND CREATE ARRAY OF EX/INLCUDED PACKAGES AND CONFIG
# FILES
#
########################################################################

def parse_file(filename):
   """
   Inside /etc/sysconfig/rhof are the filenames (absolute path) defined for
   the package black- and whitelists.

   If the files do not exist both lists stay empty. If they exists their
   content will be added in the specfile. We ignores comment lines (starting
   with '#').

   Note: Inside the files, list package name, version and release separated
   with spaces.

   Example:

   [localhost ~]$ cat /tmp/testlist 
   # black-/white-list a special release + version
   bash 3.2 24.el5.i386
   # black-/white-list a special version
   readline 5.1
   # black-/white-list the package name (all or latest version(s))
   bzip2-libs

   NOTE: Actual we only use the NAME of a blacklisted package, so all
   mentioned examples above will add the package to blacklist if the NAME
   matches, so you don't need to add version and release. For further
   information see TODO point inside func create_release_rpm.
   """

   # set back arrays of content values
   filevalues = []

   # parse file content
   try:
      filecontent = open(filename, "r")
   except:
      print "ERROR: Could not open file: " + filename
      filevalues = []
   else:
      for line in filecontent:
         line = line.rstrip('\n').rstrip(' ').strip()
         if not re.match('^#', line):
            filevalues.append(line)

      # close filehandle
      filecontent.close()

   return filevalues

def parse_excludes():
   excludes = []

   # Path to exclude files is defined inside /etc/sysconfig/rhof, could be
   # overwritten through param '-e'
   if options.exclude:
      excludes = parse_file(options.exclude)
   elif os.path.exists(BLACKLIST_FILENAME):
      excludes = parse_file(BLACKLIST_FILENAME)
   else:
      print "Warning: Blacklist file " + BLACKLIST_FILENAME + " not found."

   # TODO check if the running kernel (RPM) is in exclude list (makes no
   # sense and will lead to errors in %post)

   if options.verbose:
      print "The following packages are blacklisted:\n"
      print excludes

   return excludes

def parse_includes():
   includes = []

   # Path to include files is defined inside /etc/sysconfig/rhof, could be
   # overwritten through param '-i'
   if options.include:
      includes = parse_file(options.include)
   elif os.path.exists(WHITELIST_FILENAME):
      includes = parse_file(WHITELIST_FILENAME)
   else:
      print "Warning: Whitelist file " + WHITELIST_FILENAME + " not found."

   return includes

########################################################################
#
# MAIN FUNCTION
#
########################################################################
def main():
   connect2rhns()

   if options.sw_stack and options.systemName:
      systems = client.system.searchByName(key, options.systemName)
      if len(systems) > 1:
         sys.stderr.write("ERROR: More than one system name found matching \"" +
                          options.systemName + "\"\n")
         sys.exit(1)
      elif len(systems) == 0:
         sys.stderr.write("ERROR: No system name found matching \"" +
                          options.systemName + "\"\n")
         sys.exit(1)
      else:
         systemId = systems[0]['id']

      if options.releaseid:
         release_id = options.releaseid
         create_release_rpm(systemId, sw_stack, release_id)
      else:
         release_id = gen_releaseid()
         create_release_rpm(systemId, sw_stack, release_id)
   elif not options.systemName:
      sys.stderr.write("ERROR: Please supply a system name with option -s.\n\n")

if __name__ == "__main__":
    main()

########################################################################
#
# 
#
########################################################################

# close RHN Satellite XMLRPC connection
client.auth.logout(key)
