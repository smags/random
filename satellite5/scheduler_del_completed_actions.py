#!/usr/bin/env python
# Stefan Meyer, 16.09.2011
# Dieses Skript loescht alte archivierte Actions
# Das Skript ist zur taeglichen automatischen Ausfuehrung
# Es erfolgen keine Kommandozeilenausgaben!

import xmlrpclib
import sys
import commands
import getpass
import re
import os
import sys
import time
import optparse
from xmlrpclib import DateTime
import ConfigParser
from time import time as Time

parser = ConfigParser.SafeConfigParser()
parser.readfp(open("/etc/sysconfig/rhof", "r"))
SATELLITE_HOST = parser.get("rhof", "rhns_server")
SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST
SATELLITE_LOGIN = parser.get("rhof", "rhns_user")
SATELLITE_PASSWORD = parser.get("rhof", "rhns_password")
client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)

# define some variables
actionlist = ""

actionlist = client.schedule.listCompletedActions(key)
#actionlist = client.schedule.listArchivedActions(key)
#actionlist = client.schedule.listAllActions(key)
for entry in actionlist:
   #print str(entry['id']) + " "  + entry['type']
   actionid = int(entry['id'])
   try:
      result = client.schedule.cancelActions(key, actionid)
   except:
      result = 1

# close RHN Satellite XMLRPC connection
client.auth.logout(key)

