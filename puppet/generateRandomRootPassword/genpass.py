#!/usr/bin/env python
# Stefan Meyer, 26.05.2014
#
# This script generates a random password and writes the clear text password
# to one file per system. The systemname or fqdn must be added as a parameter
#
# It also checks on running date to compare against a weekday and time range
# in order to regenerate password or show the working one
#
###############################################################################
# import external modules
###############################################################################
from passlib.hash import sha512_crypt
from random import randrange
import sys,os,string
import getopt
import shutil
import datetime

# check if hostname was provided
if len(sys.argv) == 1:
   sys.exit(1)

###############################################################################
# global variables
###############################################################################
# The puppet master needs write access here!
passwordDir = '/var/lib/system_passwords'
hostname = sys.argv[1]
filename = passwordDir + "/" + hostname + '.txt'
backupfile = passwordDir + "/" + hostname + '.bak'

# Define time to regenerate passwd, default=Sunday
runWeekday = 6 
runStartTime = datetime.time(01, 0, 0)
runEndTime = datetime.time(23, 0, 0)

# set random password lenght
PWD_LEN = randrange(20, 40)

###############################################################################
# Functions
###############################################################################

# Function to generate Password and create the file to keep it
def generate_pass():
  # set characters, numbers and special chars to use for password
  chars = string.letters + string.digits + '+/'
  assert 256 % len(chars) == 0  # non-biased later modulo

  # generate password
  password = ''.join(chars[ord(c) % len(chars)] for c in os.urandom(PWD_LEN))

  # generate hash with random salt
  passwordhash = sha512_crypt.encrypt(password)

  # create backup
  if os.path.isfile(filename):
    shutil.copyfile(filename, backupfile)

  # create password file
  f = open(filename,'w')
  print  >> f, 'Hash: ' + str(passwordhash)
  print  >> f, 'Pass: ' + str(password)
  f.close()
  
  # print the hash
  sys.stdout.write(passwordhash)

# Function to get the Password from the file that keeps it
def get_pass():
  # read password from file as defined in global vars
  for line in open(filename,'r'):
    # Find line wih hash
    if "Hash" in line:
      # split line to obtain the password
      passwordhash = line.split(": ")[-1]
      # print pass via stdout
      # carriage return needs to be stripped off
      sys.stdout.write(passwordhash.rstrip('\n'))

# Check if weekday and running time are in range
def check_run():
  # get time and date 
  now = datetime.datetime.now()
  # check if we are running in the right weekday
  if now.weekday() == runWeekday:
    # check running time against the range
    if runStartTime <= runEndTime:
      return runStartTime <= now.time() <= runEndTime
    else:
      return runStartTime <= now.time() or now.time() <= runEndTime
  else:
    return False

###############################################################################
# Main
###############################################################################

# check if we should generate pass or reuse it
if check_run ():
  generate_pass ()
  #print "DEBUG: generate_pass"
else:
  # it's time to reuse it, but if it doesn't exist, generate one
  if os.path.isfile(filename):
    get_pass ()
    #print "DEBUG: get_pass"
  else:
    generate_pass ()
    #print "DEBUG: nofile generate_pass"
