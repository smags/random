#!/usr/bin/env python

"""
This script checks the local status of configuration files which are managed
by a RHN Satellite server. It is run on a system registered in Satellite and
uploads the status and diff to the Satellite.
"""

import commands
import httplib
import re
import sys
import urllib
import xml.sax
import xml.sax.handler

########################################################################
#
# HELPER FUNCTIONS
#
########################################################################

class SystemIdHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.inName = False
        self.inString = False
        self.inSystemId = False
        self.systemId = ''

    def startElement(self, name, attributes):
        if name == 'name':
            self.name = ''
            self.inName = True
        elif name == 'string':
            self.inString = True

    def characters(self, data):
        if self.inName:
            self.name += data
        elif self.inString and self.inSystemId:
            self.systemId += data

    def endElement(self, name):
        if name == 'name':
            self.inName = False
            if self.name == 'system_id':
                self.inSystemId = True
        elif name == 'string':
            self.inString = False
            self.inSystemId = False

def readRhnConfig():
    """
    Retrieve some values from /etc/sysconfig/rhn/up2date which we need in
    this script.
    """

    satelliteHost = None
    serverUrlRE = re.compile('serverURL=https://([^/]+)/')
    cfgIn = open('/etc/sysconfig/rhn/up2date', 'r')
    for l in cfgIn:
        m = serverUrlRE.match(l)
        if m:
            satelliteHost = m.group(1)
            break
    cfgIn.close()

    parser = xml.sax.make_parser()
    handler = SystemIdHandler()
    parser.setContentHandler(handler)
    parser.parse('/etc/sysconfig/rhn/systemid')

    systemId = re.sub('^ID-', '', str(handler.systemId))

    return (satelliteHost, systemId)

def verifyConfigFiles():
    """
    Runs rhncfg-client verify and returns a list of pairs of status and
    filename in JSON format.
    """

    cmd = "rhncfg-client verify"
    (status, output) = commands.getstatusoutput(cmd)

    if status != 0:
        sys.stderr.write("ERROR while running \"" +  cmd + "\":\n" +
                         output + "\n")
        sys.exit(status)

    files = []
    for l in output.split('\n'):
        m = re.match(' *(modified|missing) +(.*)', l)
        if m:
            (status, filename) = m.group(1, 2)
            files.append('["' + status + '", "' + filename + '"]')

    return '[' + ', '.join(files) + ']'

########################################################################
#
# MAIN FUNCTION
#
########################################################################

def main():
    (satelliteHost, systemId) = readRhnConfig()

    if satelliteHost is None:
        sys.stderr.write("ERROR: Cannot extract hostname from /etc/sysconfig/rhn/up2date serverURL\n")
        sys.exit(1)

    conn = httplib.HTTPConnection(satelliteHost)

    try:
        params = {
            'systemId': systemId,
            'files': verifyConfigFiles()
            }

        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn.request("POST", "/cgi-bin/update-config-status.cgi", 
                     urllib.urlencode(params), headers)

        response = conn.getresponse()
        responseText = response.read()
        if responseText != 'success\n':
            print "ERROR during HTTP request:", response.status, response.reason
            print responseText
    finally:
        conn.close()

if __name__ == "__main__":
    main()
