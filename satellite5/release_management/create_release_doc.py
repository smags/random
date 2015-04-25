#!/usr/bin/env python
# Stefan Meyer, 16.09.2011

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
import getopt

# Variablen
SATELLITE_HOST = "SATELLITE_HOST"
SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST

def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:],
        "h:n:f:t:",
        ["help",
         "hostname="
         "fromRelease="
         "toRelease="])

  except getopt.GetoptError, err:
    print "\n" + str(err) + "\n"
    usage()
    sys.exit(1)

  opt_hostname = None

  for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-n", "--hostname"):
        opt_hostname = a
    elif o in ("-f", "--fromRelease"):
        opt_fromRelease = a
    elif o in ("-t", "--toRelease"):
        opt_toRelease = a
    else:
        assert False, "unhandled option " + o
  errors = ""
  if not opt_hostname:
    errors += "Please specify the system with -n.\n"

  if errors != "":
    print "\n" + errors
    usage()
    sys.exit(1)

  print "Satellite User: ",
  SATELLITE_LOGIN = sys.stdin.readline()
  SATELLITE_PASSWORD = getpass.getpass("Password: ")
  SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST
  client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
  key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)

  match = re.match("^([^.]+)", opt_hostname)
  short_name = match.group(1)

  systemIDs = client.system.getId (key, opt_hostname)
  
  for system in systemIDs:
    print "SystemName: " + opt_hostname
    print "SystemID  : " + str(system['id'])
    print "Arch      : " + client.system.getCpu(key, system['id'])['arch']
    print " "

  #outfile = open("/var/www/html/pub/reports/" + opt_hostname + ".html", "w")
  outfile = open("./Release_" + opt_fromRelease + "_to_" + opt_toRelease + "_" + client.system.getCpu(key, system['id'])['arch'] +  ".html", "w")

  # outfile.write HTML header
  outfile.write("<html><head></head><style>")
  outfile.write("table {font-family: tahoma, verdana, helvetica; font-size: 90%;}")
  outfile.write("tr.table-header {background-color: #cccccc;}")
  outfile.write("tr.even {background-color: #e0e0e0;}")
  outfile.write("tr.odd {background-color: #f0f0f0;}")
  outfile.write("td {padding-left: 3px; padding-right: 3px; text-align: center;}")
  outfile.write("td.green {background-color: yellowgreen;}")
  outfile.write("td.yellow {background-color: yellow;}")
  outfile.write("td.red {background-color: red;}")
  outfile.write("</style><body><h1><center>Release Information for Release " +  client.system.getCpu(key, system['id'])['arch'] + " "  + opt_fromRelease + " to " + opt_toRelease + ".")
  outfile.write("</h1><table><tr class=\"table-header\">")
  outfile.write("<th>Name</th>")
  outfile.write("<th>Typ</th>")
  outfile.write("<th>Information</th>")
  outfile.write("</tr>")
  line = " "

  elist = client.system.getRelevantErrataByType(key, system['id'], 'Security Advisory')
  for entry in elist:
    line += "<tr class=\"odd\"><left><td><a href=\"https://" + SATELLITE_HOST + "/rhn/errata/details/Details.do?eid=" + str(entry['id']) + "\">" + entry['advisory_name'] + "</a></td>"
    line += "<left><td>" + entry['advisory_type'] + "</td>"
    line += "<left><td>" + entry['advisory_synopsis'] + "</td></tr>"

  elist = client.system.getRelevantErrataByType(key, system['id'], 'Bug Fix Advisory')
  for entry in elist:
    line += "<tr class=\"odd\"><left><td><a href=\"https://" + SATELLITE_HOST + "/rhn/errata/details/Details.do?eid=" + str(entry['id']) + "\">" + entry['advisory_name'] + "</a></td>"
    line += "<left><td>" + entry['advisory_type'] + "</td>"
    line += "<left><td>" + entry['advisory_synopsis'] + "</td></tr>"

  elist = client.system.getRelevantErrataByType(key, system['id'], 'Product Enhancement Advisory')
  for entry in elist:
    line += "<tr class=\"odd\"><left><td><a href=\"https://" + SATELLITE_HOST + "/rhn/errata/details/Details.do?eid=" + str(entry['id']) + "\">" + entry['advisory_name'] + "</a></td>"
    line += "<left><td>" + entry['advisory_type'] + "</td>"
    line += "<left><td>" + entry['advisory_synopsis'] + "</td></tr>"
  outfile.write(line.encode('utf-8'))
  outfile.write("</table>")

  outfile.write("<br><br><br>")

  outfile.write("</h1><table><tr class=\"table-header\">")
  outfile.write("<th>RPM-Name</th>")
  outfile.write("<th>Version (alt)</th>")
  outfile.write("<th>Version (neu)</th>")
  outfile.write("<th>Architektur</th>")
  outfile.write("</tr></thead>")

  plist = client.system.listLatestUpgradablePackages(key, system['id'])
  plist.sort(key=lambda plist: plist['name'])
  line = " "
  for entry in plist:
    line += "<tr class=\"odd\"><left><td>" + entry['name'] + "</td>"
    line += "<left><td>" + entry['from_version'] + "." + entry['from_release'] + "</td>"
    line += "<left><td>" + entry['to_version'] + "." + entry['to_release'] + "</td>"
    line += "<left><td>" + entry['arch'] + "</td></tr>"
  outfile.write(line.encode('utf-8'))
  outfile.write("</table>")

  outfile.write("</body></html>")
  outfile.close()
  client.auth.logout(key)



def usage():
  print """\
  Usage: create_release_doc [OPTION]
  
  Options:
  -h, --help            brief help message
  -n, --hostname=NAME   fully-qualified hostname
  -f, --from_release	from Release 
  -t, --to_release      to Release
  Creates a html file with a list of installable erratas and updates.
  """

if __name__ == "__main__":
  main()

