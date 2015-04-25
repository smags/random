#!/usr/bin/python

# this is a simple reporting script which list all systems and their
# basechans, groups and available updates, divided by RH[SBE]A type

import xmlrpclib
import ConfigParser
import cgi
import os
import re
import sys
import time
import optparse
import datetime
from datetime import date
from datetime import timedelta

# TODO offer different delemiters for CSV and HTML output

# TODO re-write it as cgi-script

# TODO only show fields defined as params for cgi script

##########################################################################   
#
# CONFIGURATION SECTION
#
##########################################################################   
parser = ConfigParser.SafeConfigParser()
parser.readfp(open("/etc/sysconfig/rhof", "r"))

# environment specific values
SATELLITE_HOST = parser.get("rhof", "rhns_server")
SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST
SATELLITE_LOGIN = parser.get("rhof", "rhns_user")
SATELLITE_PASSWORD = parser.get("rhof", "rhns_password")
# end of environment specific values

# the number of days after a systems is declared as inactive
days = 2

##########################################################################   
#
# BELOW ARE THE CODE LINES
#
##########################################################################   


# connect to RHNS server and get session key
client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)

# parseDate functions taken from oldSystens.py from spacewalk repo
# written by Jack Neely <jjneely@ncsu.edu>
def parseDate(s):
    #parseddate = iso8601.parse_date(s)
    #print "date: ", s 

#, "parsed: ", parseddate
    tuple = time.strptime(str(s), "%Y%m%dT%H:%M:%S")
    return date.fromtimestamp(time.mktime(tuple))

def search(rhn, days):
    s = rhn.server
    delta = timedelta(days=days)
    today = date.today()
    oldsystems = []
    systems = s.system.list_user_systems(rhn.session)

    for system in systems:
        #sys.stderr.write("Working on: %s  ID: %s\n" % \
        #                 (system["name"], system["id"]))

        d = parseDate(system["last_checkin"])
        if today - delta > d:
            # This machine hasn't checked in
            oldsystems.append(system)

    return oldsystems

# get the actual date
#now = str(datetime.date.today())
now = time.strftime("%Y%m%d %H:%M:%S")
#now = time.strftime("%Y%m%d")

# print HTML header
print "Content-type: text/html\n\n"
print "<html><head></head><body>"
print "<br /><br /><h1>Last update: " + now + "</h1><br />"
print "<table border=\"1\">"
print "<thead><tr>"

# we have to give each param an own column
# additional we have to default colums: 'No' and 'Name'
print "<th>No</th>"
print "<th>Name</th>"
print "<th>Checked in</th>"
print "<th>CPU</th>"
print "<th>CPU-MODEL</th>"
print "<th>MEMORY</th>"

# close the table head row
print "</tr></thead>"
#print "Name\tID\tLastLogin\tBaseChan\tRHSA\tRHBA\tRHEA"

# check the RHNS version because the calls differ at some points
rhnsversion = client.api.systemVersion()
if re.match('^5.2', rhnsversion):
   # print "RHNS Server has version 5.2"
	rhnsver = "5.2"
elif re.match('^5.3', rhnsversion):
   rhnsver = "5.3"
else:
	print "RHNS Server has unsupported version: ", rhnsver
	sys.exit(0)

systemnr = 0

systemlist = client.system.listUserSystems(key)
for system in systemlist:
   systemnr += 1 
   sysid = int(system['id'])
	
   ##########################################################################   
   #
   # HTML OUTPUT GENERATION
   #
   ##########################################################################   
   line = "" 
   # concatenate the complete line
   line = "<tr>"
   line += "<td>" + str(systemnr) + "</td>"
   line += "<td><a href=\"https://" + SATELLITE_HOST + "/rhn/systems/details/Overview.do?sid=" + str(system['id' ]) + "\">" + system['name'] + "</a></td>"

   # last checkin-date
   try:
      checkin = client.system.getName(key, sysid)['last_checkin']
      line += "<td>" + str(checkin) + "</td>"
   except:
      line += "<td bgcolor=\"red\">unknown</td>"


   # CPU Count
   try:
      cpucz = client.system.getCpu(key, sysid)['count']
      line += "<td>" + str(cpucz) + "</td>"
   except:
      line += "<td bgcolor=\"red\">NN</td>"

   # CPU Modell
   try:
      cpuc = client.system.getCpu(key, sysid)['model']
      line += "<td>" + cpuc + "</td>"
   except:
      line += "<td bgcolor=\"red\">unknown</td>"
   
# List Memory
   try:
      mem = client.system.getMemory(key, sysid)['ram']
      line += "<td>" + str(mem) + " MB" + "</td>"
   except:
      line += "<td bgcolor=\"red\">NN</td>"


   # print the complete row and close HTML tag for table row
   print line.encode('latin1')
   print "</tr>"

# close table tags
print "</table>"

# Attention. 
# print "<br /><br /><h3>Actually you can refresh the script using: python /var/www/cgi-bin/report-klv.py > /var/www/html/pub/report-klv.htm</h3><br />"

# END OF CODE LINES


# close HTML tags
print "</body></html>"

client.auth.logout(key)

