#!/usr/bin/env python

# This script schedules remote commands for all|a single system(s)|system group.
# The content of the scheduled action is the content of the script (param).

# TODO implement include list (filename)
# TODO reporting / tracking
# TODO vizualiation of reporting

import xmlrpclib
import sys
import commands
import getpass
import re
import os
import sys
import time
import csv
from xmlrpclib import DateTime
from time import time as Time
import ConfigParser
from optparse import OptionParser
scriptparser = OptionParser()

parser = ConfigParser.SafeConfigParser()
parser.readfp(open("/etc/sysconfig/rhof", "r"))

SATELLITE_HOST = parser.get("rhof", "rhns_server")
SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST
SATELLITE_LOGIN = parser.get("rhof", "rhns_user")
SATELLITE_PASSWORD = parser.get("rhof", "rhns_password")

# the statusfile to store temporary status information of scheduled actions
# Note: To make parallel scheduling possible we add as a suffix to the filename
# defined below the releaseid or if not set the date-time of the action (YYMMDDHHMM)
global statusfile
statusfile = "/var/tmp/schedule_status"   

# define some variables
systemlist = []
success_ops = 0
failed_ops = 0
failed_systems = []
date8601 = DateTime(Time())
needed = 'provisioning_entitled'

###############################################################################################
#
# SCRIPT OPTIONS
#
###############################################################################################
scriptparser.add_option("-u", "--user", dest="scriptuser", default="root", help="Username to run the remote script. Default: root")
scriptparser.add_option("-g", "--group", dest="scriptgroup", default="root", help="Groupname to run the remote script. Default. root")
scriptparser.add_option("-t", "--timeout", dest="scripttimeout", default=3600, help="Timeout to wait for running remote script. Default: 3600")
scriptparser.add_option("-G", "--servergroup", dest="servergroup", help="Servergroupname where the script should run. Note: you have to quote if group name contains blanks")
scriptparser.add_option("-S", "--system", dest="system", help="Systemname oder regular expression to get a system list matching this regexp")
scriptparser.add_option("-e", "--exclude", dest="exclude", help="Filename of exlude file containing system ID or hostnames of systems to exclude")
scriptparser.add_option("-r", "--releaseid", dest="releaseid", help="The releaseid the action is defined with. If not given date-time would be taken for filename of statusfile.")
scriptparser.add_option("-R", "--report", dest="report", help="Report a running / completed schedule action.", default=False, action="store_true")
scriptparser.add_option("-F", "--filename", dest="filename", help="The filename of statusfile we should report. Only in combination with option '--report'.")

scriptparser.add_option("-f", "--force", dest="forcerun", help="Scheduling remote command without interactive confirmation. Be careful with this option.", default=False, action="store_true")
scriptparser.add_option("-v", "--verbose", dest="verbose", help="Enable debugging output", default=False, action="store_true")

# DOKU: Some examples:
# runRemoteCommand.py /tmp/test.sh -G 'App DB2'		<- all members of group (actual: 2)
# runRemoteCommand.py /tmp/test.sh -S lde5505q		<- 1 single system
# runRemoteCommand.py /tmp/test.sh -S lde5			<- ~ 10 systems

# parse command line options
(options, args) = scriptparser.parse_args()
scriptuser = options.scriptuser
scriptgroup = options.scriptgroup
scripttimeout = int(options.scripttimeout)

# TODO HELP / DOKU: note that you have to mask group names, e.g.: -G 'App DB2'

###############################################################################################
#
# CHECK REQUIREMENTS
#
###############################################################################################
# check if we have a filename for remote script, only exeption is --report
if len(args) < 1:
   if not options.report:
      scriptparser.error("We need at least one param: Filename of remote script")
else:
   # the filename is the first argument
   filename = args[0]

   # check if file exists and is readable
   try:
      fobj = open(filename, "r")
      script = fobj.read()
      fobj.close()
   except:
      print "ERROR: Could not open file %s for reading." % filename
      sys.exit(1)

# calculate filename of statusfile
actdate = time.strftime("%Y%m%d%H%M%S")
if options.releaseid:
   statusfile = statusfile + '-' + str(options.releaseid)
elif options.filename:
   statusfile = options.filename
else:
   statusfile = statusfile + '-' + actdate 
# print filename
if options.verbose:
   print "Path for status file: " + statusfile
# TODO check if already exists, if yes, try to delete

# check if exclude file exists if option is given
if options.exclude and not os.access(options.exclude, os.R_OK):
   print "ERROR: Could not open exclude file %s for reading." % options.exclude
   sys.exit(1)

# TODO check if script has a shebang line, if not, add a default one
#script = "#!/bin/sh\n" + command + "\n"

###############################################################################################
#
# HELPER FUNCTIONS
#
###############################################################################################
# Function find_sysid 
#def find_sysid(hostname):

def report():
   if options.filename or options.releaseid:
      # check if file is writeable
      #statusfile = options.filename
      if not os.access(statusfile, os.R_OK):
         print "Statusfile not found or no write permissions: " + statusfile
         sys.exit(1)
      elif options.verbose:
         print "Statusfile found and has write permissions: " + statusfile
   else:
      print "Neither a statusfile (option '-F') nor a release (option '-r') is given. Trying to find statusfiles."
      # try to find out all running releases (all files matching regexp '^statusfile.*'

      # the status is 'Completed' if there is no action with status 'R' (Running) left

   # parse the statusfile
   entries = open(statusfile)
   fields = ['sysid', 'actionid', 'sched', 'status', 'pickedup', 'completed', 'msg']
   data = csv.DictReader(entries, fields, delimiter=':')
   
   for entry in data:
      # we are only interested in entries with status 'R' (Running)
      if entry['status'] == 'R':
         # get the status / result of this action using the actionid
         try:
            actstatus = client.system.getScriptResults(key, int(entry['actionid']))
         except:
            print "Could not get status of action with actionid: " + str(entry['actionid'])
         # parse the result: 
         print "RC of action " + str(entry['actionid']) + " is:", actstatus[0].get('returnCode')
         if actstatus[0].get('returnCode') == 0:
            # success
            newstatus = 'S'
         else:
            newstatus = 'F'
            newmsg = 'Error message: ' + str(actstatus[0].get('output'))

   # write the actual results back to hash 
   # data.update

   # write the actual results back to statusfile

   # TODO implement this function and remove exit
   print "\n\nThis function is not implemented yet. Exit.\n"
   sys.exit(2)


###############################################################################################
#
# RHN SATELLITE LOGIN
#
###############################################################################################

# RHN Satellite Login and get session key
if options.verbose:
   print "Connecting to RHN Satellite Server %s with Login %s" % (SATELLITE_URL, SATELLITE_LOGIN)
client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
try:
   key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)
except:
   print "Could not connect to RHN Satellite Server %s with Login %s" % (SATELLITE_URL, SATELLITE_LOGIN)
   sys.exit(1)

###############################################################################################
#
# SCRIPT OPTIONS PARSER
#
###############################################################################################

# depending on options we run the remote command at:
# 	- a single sytem or a group of system matching the regexp (Param: '-S')
# 	- a sytem group (Param: '-G')
# 	- all sytems (NO Param needed)

# TODO make it multi value aware (N system / system groups)
if options.system:
   print "Target is regular expression for searching systems: " + str(options.system)
   try:
      allsystems = client.system.searchByName(key, str(options.system))
      for system in allsystems:
         systemlist.append(int(system['id']))
   except:
      print "Could not find system with system name " + str(options.system)
      sys.exit(1)  
elif options.servergroup:
   print "Target is server group(s): " + str(options.servergroup)
   try:
      groupmembers = client.systemgroup.listSystems(key, str(options.servergroup))
      for system in groupmembers:
         systemlist.append(system['id'])
   except:
      print "Could not find group %s. Please check if group name is correct." % str(options.servergroup)
      sys.exit(1)
elif options.report:
   # call helper function report
   report()
else:
   print "Neither system nor system group defined. Schedule script on all systems."
   allsystems = client.system.listUserSystems(key)
   for system in allsystems:
      systemlist.append(int(system['id']))



###############################################################################################
#
# PARSE EXCLUDE FILE AND CREATE ARRAY OF EXLCUDED SYSTEMS
#
###############################################################################################
if options.exclude:
   exclude_systems = []
   try:
      excludefile = open(options.exclude, "r")
      #excludelist = excludefile.read()
   # even if we already checked this
   except:
      print "ERROR: Could not open exclude file: " + options.exclude
   else:
      for line in excludefile:
         line = line.rstrip('\n').rstrip(' ').strip().lower()
         if re.match('^\d+$', line):
            if options.verbose:
               print "Exlude entry " + str(line) + " does contain only digits, assuming this is a system id."
            # only digits, assuming this is a system id
            exclude_systems.append(int(line))
         else:
            if options.verbose:
               print "Exlude entry " + str(line) + " does not contain only digits, assuming this is a profile name."
               # search for sysid
            try:
               sysfound = client.system.searchByName(key, str(line))
            except:
               print "ERROR: Invalid entry in exclude file: " + str(line) + " (neither a system id nor an existing profile name). Skipping entry." 
               # pass
            else:
               for systemfound in sysfound:
                  exclude_systems.append(int(systemfound['id']))

      # close filehandle
      excludefile.close()

      if options.verbose:
         print "\nThe following system (ID)s are excluded: \n"
      for system in exclude_systems:
         try:
            profile_name = client.system.getDetails(key, system)['profile_name'] 
         except:
            profile_name = "UNKNOWN. Does such a system really exists?"

         if system in systemlist:
            systemlist.remove(system)
            if options.verbose:
               print " - " + profile_name + " ("  + str(system) + "): Removed from system list"
         else:
            if options.verbose:
               print " - " + profile_name + " ("  + str(system) + "): Not in system list"


#sys.exit(1)

###############################################################################################
#
# BUILDING SYSTEM LIST AND PRINT / ASK FOR CONFIRMATION IF NOT OPTION --FORCE
#
###############################################################################################

# default case: interactive ask user if we should schedule action
if not options.forcerun:
   # ask twice: 1st for system list and 2nd for script content verify
   answer = raw_input("\nThe action will be scheduled at " + str(len(systemlist)) + " systems, press ENTER or 'p' to see the complete list.")
   if answer == "p":
      print "\nSystem list: \n"
      for system in systemlist:
         print " - " + str(system) + "  (" + client.system.getDetails(key, system)['profile_name'] + ")"
      print ""	  

   # ask if ok or user want to see list of systems
   answer = raw_input("Should the remote command be scheduled now at these systems? (y|n)")
   if answer == "y":
      print "Scheduling remote command now."
   else:
      print "Won't schedule it now. Exit."
      sys.exit(1)
# special case: option force: non-interactive schedule action
else:
   print "\nOption '--force' selected. Scheduling remote commands without confirmation now.\n"
   print "\nSystem list: \n"
   for system in systemlist:
      print " - " + str(system) + "  (" + client.system.getDetails(key, system)['profile_name'] + ")"
   print ""	  


###############################################################################################
#
# ITERATE THROUGH ALL SYSTEM IN TARGET LIST
#
###############################################################################################

# open file handle for statusfile
fobj = open(statusfile, "w")

for sysid in systemlist:

   # check if our system has the needed provisioning entitlement
   entitlements = []
   entitlements = client.system.getEntitlements(key, sysid)
   if needed in entitlements:
      if options.verbose:
         print "Server with ID %s has a provisioning entitlement. Proceeding..." % (sysid)

      actionid = client.system.scheduleScriptRun(key, sysid, scriptuser, scriptgroup, scripttimeout, script, date8601)
      if actionid is None:
         print "ERROR: Remote command could not scheduled succesfully at system: ", sysid
         failed_ops += 1	  
         failed_systems.append(sysid)
         msg = str(sysid) + "::" + actdate + ":F:::Remote command could not be scheduled.\n"
         fobj.write(msg)
      else:
         print "Remote command succesfully scheduled: https://" + SATELLITE_HOST + "/network/systems/details/history/event.pxt?sid=" + str(sysid) + "&hid=" + str(actionid)
         #print "Remote command succesfully scheduled  at system %s with actionid: %s " % (str(sysid), str(actionid))
         success_ops += 1

         # add the result to dictionary with key:value sysid:actionid
         msg = str(sysid) + ":" + str(actionid) + ":" + actdate + ":R:::Remote command scheduled.\n"
         fobj.write(msg)
         # TODO store this action id in a file or whatever to track the running actions later 		 
   else:
      print "Server with ID %s does NOT have a provisioning entitlement. Skipping..." % (sysid)
      failed_ops += 1
      failed_systems.append(sysid)

      msg = str(sysid) + "::" + actdate + ":F:::Server has no provisioning entitlement.\n"
      fobj.write(msg)

fobj.close()

# print the first results
print "\n\n====== SUMMARY ====== \n\n"
if failed_ops > 0:
   print "Scheduling failed for %s systems: " % str(failed_ops)
   for system in failed_systems:
      print " - " + str(system) + "  (" + client.system.getDetails(key, system)['profile_name'] + ")"
   print ""
   
print "Action successfully scheduled at %s systems: \n" % str(success_ops)


# close RHN Satellite XMLRPC connection
client.auth.logout(key)

