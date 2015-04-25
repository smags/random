#!/usr/bin/env python

# Export provisioning data from a Red Hat Network Satellite. This includes
# configuration channels, activation keys and Kickstart profiles.

# import modules
import ConfigParser
import getopt
import simplejson as json
import os
import re
import shutil
import sys
import termios
import tty
import xmlrpclib
import datetime
import string
import commands

########################################################################
# environment-specific configuration

parser = ConfigParser.SafeConfigParser()
parser.readfp(open("/etc/sysconfig/rhof", "r"))

SATELLITE_HOST = parser.get("rhof", "rhns_server")
SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST
SATELLITE_USER = parser.get("rhof", "rhns_user")
SATELLITE_PASSWORD = parser.get("rhof", "rhns_password")

STAGE1_NAME = parser.get("config", "stage1")
STAGE2_NAME = parser.get("config", "stage2")
STAGE3_NAME = parser.get("config", "stage3")

STAGE1_LABEL = str.lower(STAGE1_NAME)
STAGE2_LABEL = str.lower(STAGE2_NAME)
STAGE3_LABEL = str.lower(STAGE3_NAME)

STAGE1_USER = None
STAGE1_PASSWORD = None
if parser.has_option("rhof", "stage1_user"):
    STAGE1_USER = parser.get("rhof", "stage1_user")
    STAGE1_PASSWORD = parser.get("rhof", "stage1_password")

STAGE2_USER = None
STAGE2_PASSWORD = None
if parser.has_option("rhof", "stage2_user"):
    STAGE2_USER = parser.get("rhof", "stage2_user")
    STAGE2_PASSWORD = parser.get("rhof", "stage2_password")

STAGE3_USER = None
STAGE3_PASSWORD = None
if parser.has_option("rhof", "stage3_user"):
    STAGE3_USER = parser.get("rhof", "stage3_user")
    STAGE3_PASSWORD = parser.get("rhof", "stage3_password")

SW_LABEL_PREFIX = str.lower(parser.get("config", "prefix_sw"))

# 2010-07-05 stephand: TODO get from config
SW_CLONE_PREFIX = "clone"

# 2010-07-07 stephand: TODO get from config
ARCHS_REX = "i386|x86_64"

# 2010-07-05 stephand: TODO get from config
SW_CHANNEL_STORE_PREFIX = "/var/satellite"

# 2010-07-13 stephand: TODO get from config
PKG_BLACKLIST_FILE = '/etc/sysconfig/rhof_pkg_blacklist'
PKG_WHITELIST_FILE = '/etc/sysconfig/rhof_pkg_whitelist'

BASEOS_CHANS_RH_REX = parser.get("config", "baseos_chans_rh_rex")

def main():
    global client
    global session
    global PKG_BLACKLIST_FILE
    global PKG_WHITELIST_FILE
    global SATELLITE_USER
    global SATELLITE_PASSWORD

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hd:S:r:lkcmis:b:", 
                                   ["help",
                                    "user=",
                                    "password=",
                                    "directory=",
                                    "stage=",
                                    "service=",
                                    "arch=", 
                                    "list-services",
                                    "kickstart",
                                    "local-config",
                                    "activation-keys",
                                    "config-channels",
                                    "software-channels",
                                    "merge",
                                    "interactive",
                                    "export-merged",
                                    "everything",
                                    "list-swstacks",
                                    "list-basechannels",
                                    "pkg-blacklist-file=",
                                    "pkg-whitelist-file="])
    except getopt.GetoptError, err:
    	print "\n" + str(err) + "\n"
        usage()
        sys.exit(1)

    opt_directory = None
    opt_stage = 'all'
    opt_arch = 'all'
    opt_service = 'all'
    opt_kickstart = False
    opt_localConfig = False
    opt_activation_keys = False
    opt_config_channels = False
    opt_merge = False
    opt_interactive = False
    opt_exportMerged = False
    opt_software_channels = False
    opt_everything = False
    user_override = False

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-u", "--user"):
            SATELLITE_USER = a
            user_override = True
        elif o in ("-p", "--password"):
            SATELLITE_PASSWORD = a
        elif o in ("-d", "--directory"):
            opt_directory = a
        elif o in ("-l", "--list-services"):
            listServices()
            sys.exit()
        elif o in ("--list-swstacks"):
            listSwStacks()
            sys.exit()
        elif o in ("--list-basechannels"):
            listBaseChannels()
            sys.exit()
        elif o in ("-S", "--stage"):
            opt_stage = a
        elif o in ("-r", "--service"):
            opt_service = a
        elif o in ("-k", "--kickstart"):
            opt_kickstart = True
        elif o in ("-c", "--local-config"):
            opt_localConfig = True
        elif o in ("-m", "--merge"):
            opt_merge = True
        elif o in ("-i", "--interactive"):
            opt_interactive = True
        elif o in ("-s", "--software-channels"):
            opt_software_channels = True
        elif o == '--arch':
            opt_arch = a
        elif o == "--export-merged":
            opt_exportMerged = True
        elif o == "--pkg-blacklist-file":
            PKG_BLACKLIST_FILE = a
        elif o == "--pkg-whitelist-file":
            PKG_WHITELIST_FILE = a
        elif o == '--activation-keys':
            opt_activation_keys = True
        elif o == '--config-channels':
            opt_config_channels = True
        elif o == "--everything":
            opt_everything = True
        else:
            assert False, "unhandled option " + o

    if not opt_directory:
        print "\nPlease specify a destination directory to write the export to"
        print "with option -d.\n"
        sys.exit(1)

    if opt_stage not in (STAGE1_LABEL, STAGE2_LABEL, STAGE3_LABEL, 'all'):
        print "\nPlease specify the lifecycle stage to export.\n"
        print "Available stages are: " + STAGE1_LABEL + ", " + \
            STAGE2_LABEL + ", " + STAGE3_LABEL + ", all\n"
        sys.exit(1)

    if opt_merge and opt_stage == 'all':
        print "\nTo merge software channels, please specify a lifecycle\n"
        print "stage other than \"all\" with parameter -S."
        sys.exit(1)

    # If the user has not specified a Satellite user, and if the
    # configuration file defines a user for the chosen stage, use that
    # instead of the default user.
    if not user_override and not opt_merge:
        if opt_stage == STAGE1_LABEL and STAGE1_USER is not None:
            SATELLITE_USER = STAGE1_USER
            SATELLITE_PASSWORD = STAGE1_PASSWORD
        elif opt_stage == STAGE2_LABEL and STAGE2_USER is not None:
            SATELLITE_USER = STAGE2_USER
            SATELLITE_PASSWORD = STAGE2_PASSWORD
        elif opt_stage == STAGE3_LABEL and STAGE3_USER is not None:
            SATELLITE_USER = STAGE3_USER
            SATELLITE_PASSWORD = STAGE3_PASSWORD

    # Connect to Satellite.
    client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
    session = client.auth.login(SATELLITE_USER, SATELLITE_PASSWORD)

    if opt_everything:
        if opt_service == 'all' or opt_service == 'baseos' :
            opt_kickstart = True
            opt_activation_keys = True
            opt_config_channels = True
            opt_merge = True
            opt_exportMerged = True
            opt_software_channels = True
        else:
            opt_kickstart = True
            opt_activation_keys = True
            opt_config_channels = True
            opt_software_channels = True            

    if opt_config_channels:
        configChannels = \
            exportConfigChannels(opt_stage, opt_service, opt_directory)
        for label in configChannels:
            dumpJSON(opt_directory + "/config_files/" + label + ".json", 
                     configChannels[label])

    if opt_activation_keys:
        activationKeys = exportActivationKeys(opt_stage, opt_service, opt_arch)
        mkdir(opt_directory + "/activation_keys")
        for label in activationKeys:
            dumpJSON(opt_directory + "/activation_keys/" + label + ".json",
                     activationKeys[label])

    if opt_kickstart:
        kickstartProfiles = exportKickstartProfiles(opt_stage, opt_arch)
        mkdir(opt_directory + "/kickstart_profiles")
        for label in kickstartProfiles:
            dumpJSON(opt_directory + "/kickstart_profiles/" + label + ".json", 
                     kickstartProfiles[label])

    if opt_localConfig:
        localFiles = exportLocalFiles(opt_directory)
        dumpJSON(opt_directory + "/local-files.json", localFiles)

    if opt_software_channels:
        swchannel_results = \
            exportSwChannels(opt_stage, opt_service, opt_arch, opt_directory)

        for label in swchannel_results:
            dumpJSON(opt_directory +  "/software_channels/" + label + ".json", 
                     swchannel_results[label])

    if opt_merge:
        if not (opt_software_channels and opt_service in ['all','baseos']):
            # corp. channel was not yet exported
            swchannel_results = \
                exportSwChannels(opt_stage, 'baseos', opt_arch, opt_directory)

            for label in swchannel_results:
                dumpJSON(opt_directory +  "/software_channels/" + \
                             label + ".json", 
                         swchannel_results[label])

        merged_tgt_channels = \
            mergeSWChannels(opt_stage, opt_arch, opt_interactive)

        if opt_exportMerged:
            if not merged_tgt_channels:
                print "Warning: No Channels were merged, not running rhn-satellite-exporter"
            else:
                runSatExporter(merged_tgt_channels, opt_directory)
                dumpJSON(opt_directory + "/rhn-sat-export/rhnsat-exported-channels.json", merged_tgt_channels)
                sat_exported_errata = getErrataLists(merged_tgt_channels)
                dumpJSON(opt_directory + "/rhn-sat-export/rhnsat-exported-channels-errata.json", sat_exported_errata)


def usage():
    print """\
  export-provisioning.py [options]

  Options:
    -h, --help              brief help message
    -l, --list-services     list service stacks defined on the Satellite
    --list-swstacks         list software stacks defined on the Satellite
    --list-basechannels     list base channels
    -d, --directory=DIRECTORY  destination directory
    -S, --stage=STAGE       stage to export
    -r, --service=SERVICE   service stack to export,
                            SERVICE=all|baseos|<service>|<service>-<app>
    --arch                  Architecture to export (i386|x86_64), default: all
    -k, --kickstart         export Kickstart profiles for given stage
    -c, --local-config      export local configuration files
    --activation-keys       export Activation Keys
    --config-channels       export Config Channels
    -s, --software-channels export Custom Software Channels
    -m, --merge             merge base and child software channels to next stage
    -i, --interactive       prompt for each channel before merging
    --export-merged         export merged channels using rhn-satellite-exporter
                            (default: no)
    --pkg-blacklist-file    package blacklist file
                            (default: /etc/sysconfig/rhof_pkg_blacklist)
    --everything            is a shortcut for
                              --kickstart --activation-keys --config-channels 
                              --software-channels
                            if --service=all (default) or --service=baseos then
                            all of the above plus --merge --export-merged  
"""


def listServices():
    """
    List all services that are defined in Satellite, including the Base OS.
    """

    print "Service stacks defined on " + SATELLITE_HOST
    print "for user " + SATELLITE_USER + ":\n"

    allChannels = sorted(client.channel.listAllChannels(session), 
                         lambda c1,c2: cmp(c1['label'], c2['label']))

    services = []
    for c in allChannels:
        label = c['label']
   
        match = re.match("^" + SW_LABEL_PREFIX + "-type-([^-]+)-", label)
        if match and match.group(1):
            services.append(match.group(1))

    if services:
        # Temporarily convert the list to a set, to remove duplicates.
        services = list(set(services))
        services.sort()

        print "baseos"
        for s in services:
            print s

def getSwStacks():
    """
    Return all Custom Software Stacks that are defined in Satellite
    """

    allChannels = sorted(client.channel.listAllChannels(session), 
                         lambda c1,c2: cmp(c1['label'], c2['label']))

    sw_stacks = {}
    for c in allChannels:
        label = c['label']
   
        match = re.match("^" + SW_LABEL_PREFIX + "-type-([^-]+)-([^-]+)-([^-]+)-([^-]+)$", label)
        if match and match.group(1) and match.group(2) and match.group(3) and match.group(4):
            #services.append(match.group(1))
            service = match.group(1)
            app = match.group(2)
            stage = match.group(3)
            arch = match.group(4)
            if service not in sw_stacks:
                sw_stacks[service] = {}
            if app not in sw_stacks[service]:
                sw_stacks[service][app] = {}
            if stage not in sw_stacks[service][app]:
                sw_stacks[service][app][stage] = {}
            sw_stacks[service][app][stage][arch] = label

    return sw_stacks
            
def listSwStacks():
    """
    List all Custom Software Stacks that are defined in Satellite
    """

    print "Software stacks defined on " + SATELLITE_HOST
    print "for user " + SATELLITE_USER + ":\n"

    allChannels = sorted(client.channel.listAllChannels(session), 
                         lambda c1,c2: cmp(c1['label'], c2['label']))

    sw_stacks = []
    for c in allChannels:
        label = c['label']
   
        match = re.match("^" + SW_LABEL_PREFIX + "-type-([^-]+)-([^-]+)-([^-]+)-([^-]+)$", label)
        if match and match.group(1) and match.group(2) and match.group(3) and match.group(4):
            service = match.group(1)
            app = match.group(2)
            sw_stacks.append(service + '-' + app)

    if sw_stacks:
        # Temporarily convert the list to a set, to remove duplicates.
        sw_stacks = list(set(sw_stacks))
        sw_stacks.sort()

        for s in sw_stacks:
            print s

def listBaseChannels():
    """
    List base channels that are defined in Satellite
    """

    print "Base Channels defined on " + SATELLITE_HOST
    print "for user " + SATELLITE_USER + ":\n"
    
    channel_tree = getSWChannelTree()
    
    for base_channel in channel_tree:
        print base_channel
        for child_channel in channel_tree[base_channel]:
            print "    " + child_channel

def exportConfigChannels(stage, service, directory):
    """    
    Export all, some or one configuration channel
    The selection of the channels to export is done by stage and
    service, where service can be given as
    all|baseos|<servicename>|<servicename>-<appname>
    
    Metadata is returned as a dict (key: label), so that it can be
    used to write one json file for each exported config channel
    """

    if stage == 'all':
        labelPrefix = ''
    else:
        if service == 'baseos':
            labelPrefix = "^cfg-stage-" + stage
        elif service == "all":
            labelPrefix = "^cfg-stage-" + stage + \
                "|^cfg-type-([^-]+)(-[^-]+)?-" + stage
        else:
            # this rex works with either service only or service-app
            labelPrefix = "^cfg-type-" + service + "(-[^-]+)?-" + stage

    result = {}

    allChannels = client.configchannel.listGlobals(session)
    for c in allChannels:
        label = c['label']

        if not re.match(labelPrefix, label):
            continue
        
        exported_cfg_channel = exportConfigChannelByLabel(c, directory)
        result[label] = exported_cfg_channel
    
    return result

def exportConfigChannelByLabel(cfg_channel, directory):
    """
    Export one config channel given by its label
    This is needed to be able to export all, some or only one
    """
    
    result = []
    label = cfg_channel['label']
    print "\nExporting " + label

    pathPrefix = directory + "/config_files/" + label

    # Remove any existing directory for this configuration channel, so
    # we don't keep obsolete files from a previous export.
    try:
        shutil.rmtree(pathPrefix)
    except OSError:
        pass

    files = client.configchannel.listFiles(session, label)
    filePaths = map(lambda f: f['path'], files)

    try:
        fileInfos = client.configchannel.lookupFileInfo(session, label, filePaths)
    except:
        # Due to bugs in the Satellite API, the lookupFileInfo call may
        # fail. In this case, repeat it for each file in turn, so the user
        # at least knows which file causes the problem.
        print "\nconfigchannel.lookupFileInfo failed with " + \
            str(sys.exc_info()[0])
        print "If the error below mentions an \"invalid token\", check the file"
        print "for non-printable characters and try to set its type"
        print "to \"binary\" in the Satellite Web UI.\n"

        for p in filePaths:
            print "Trying to get file info for " + p + " ...",
            client.configchannel.lookupFileInfo(session, label, [p])
            print "OK"

        sys.exit(1)

    if fileInfos:
        downloadConfigFiles(label, directory + "/config_files")

    exportedFiles = []

    for f in fileInfos:
        isBinary = False
        macroStartDelimiter = ''
        macroEndDelimiter = ''

        if f['type'] == 'file':
            isBinary = f['binary']
	    if not isBinary:
            	macroStartDelimiter = f['macro-start-delimiter']
            	macroEndDelimiter = f['macro-end-delimiter']

	if f['type'] == 'symlink':
	    exportedFiles.append({
		'path': f['path'],
		'type': f['type'],
		'target_path': f['target_path']})
	else:
	    permissionsMode = f['permissions_mode']
	    owner = f['owner']
	    group = f['group']

            exportedFiles.append({
                'path': f['path'],
                'type': f['type'],
                'binary': isBinary,
                'permissions_mode': permissionsMode,
                'owner': owner,
                'group': group,
                'macro-start-delimiter': macroStartDelimiter,
                'macro-end-delimiter': macroEndDelimiter})

    result.append({
            'label': label,
            'name': cfg_channel['name'],
            'description': cfg_channel['description'],
            'files': exportedFiles})

    return result

def exportActivationKeys(stage, service, arch):
    """
    List the current activation keys for the given stage and software
    service stack. This includes all information like packages, child
    channels and system groups.
    
    changed: now return dict instead of list to enable storing one
             JSON file for each key
    """

    if stage == 'all':
        # We still have to check for a leading number. Otherwise,
        # we would also get the system reactivation keys.
        keyPrefix = "^[0-9]+-"
    else:
        if service == 'baseos':
            # We don't have any activation keys for the Base OS.
            return {}
        elif service == 'all':
            keyPrefix = "^[0-9]+-(type-([^-]+)(-[^-]+)?|stage)-" + stage
        else:
            keyPrefix = "^[0-9]+-type-" + service + "(-[^-]+)?-" + stage
        
    if arch != 'all':
        keyPrefix += "-[^-]+-" + arch

    result = {}

    allKeys = client.activationkey.listActivationKeys(session)

    groupNames = {}
    for g in client.systemgroup.listAllGroups(session):
        groupNames[g['id']] = {
            'name': g['name'],
            'description': g['description']}

    for k in allKeys:
        label = k['key']

        if not re.match(keyPrefix, label):
            continue

        # Check if this is one of the automatically created reactivation
        # keys.
        if re.match("^Kickstart re-activation key for ", k['description']) or \
		   re.match("^Automatically generated activation key", k['description']):
            continue

        print "Exporting " + label

        configDeployment = \
            client.activationkey.checkConfigDeployment(session, label)

        configChannels = []
        if "provisioning_entitled" in k['entitlements']:
            configChannels = client.activationkey.listConfigChannels(session, label)
            configChannels = map(lambda c: c['label'], configChannels)

        # Map the list of group IDs to name/description.
        groups = map(lambda id: groupNames[id], k['server_group_ids'])

        # Remove the organization prefix, as we might want to import this
        # into a different organization.
        label = re.sub("^[0-9]+-", "", label)

        result[label] = {
                'key': label,
                'usage_limit': k['usage_limit'],
                'base_channel_label': k['base_channel_label'],
                'universal_default': k['universal_default'],
                'config_deployment': configDeployment,
                'description': k['description'],
                'child_channel_labels': k['child_channel_labels'],
                'entitlements': k['entitlements'],
                'packages': k['packages'],
                'config_channels': configChannels,
                'groups': groups}
                
    return result


def exportKickstartProfiles(stage, arch):
    """
    Return all Kickstart profiles for the given stage as a list.
    """

    result = {}

    if stage == 'all':
        labelPrefix = ''
    else:
        labelPrefix = "^ks-stage-" + stage

    if arch != 'all':
        labelPrefix += "-.*" + arch

    for p in client.kickstart.listKickstarts(session):
        label = p['label']

        if not re.match(labelPrefix, label):
            continue

        print "Exporting " + label

        # For some fields, the Satellite API returns the data in random
        # order, and the order changes each time we call the API. We want to
        # store our output in a version control system, so the output must
        # stay the same if the provisioning data has not changed. We solve
        # this by sorting the data where this happens alphabetically.

        advancedOptions = \
            client.kickstart.profile.getAdvancedOptions(session, label)
        advancedOptions = sorted(advancedOptions,
                      lambda o1, o2: cmp(o1['name'], o2['name']))

        customOptions = \
            client.kickstart.profile.getCustomOptions(session, label)
        customOptions = map(lambda o: o['arguments'], customOptions)

        activationKeys = \
            client.kickstart.profile.keys.getActivationKeys(session, label)

        # For activation keys, we only export the "key" label. From this, we
	# also remove the organization prefix, as we might want to import
	# the data into a different organization.
        activationKeys = \
            map(lambda k: re.sub("^[0-9]+-", "", k['key']), activationKeys)

        packages = \
            client.kickstart.profile.software.getSoftwareList(session, label)

        scripts = []
        for s in client.kickstart.profile.listScripts(session, label):
            scripts.append({
                    'contents': s['contents'],
                    'script_type': s['script_type'],
                    'interpreter': s['interpreter'],
                    'chroot': s['chroot']})
        scripts = sorted(scripts,
                         lambda s1,s2: cmp(s1['contents'], s2['contents']))

        configManagement = \
            client.kickstart.profile.system.checkConfigManagement(session, label)
        remoteCommands = \
            client.kickstart.profile.system.checkRemoteCommands(session, label)
        seLinux = client.kickstart.profile.system.getSELinux(session, label)
        locale = client.kickstart.profile.system.getLocale(session, label)

        partitioning = client.kickstart.profile.system.getPartitioningScheme(
            session, label)
        partitioning = sorted(partitioning)

        keys = client.kickstart.profile.system.listKeys(session, label)
        keys = sorted(keys,
                      lambda k1, k2: cmp(k1['description'], k2['description']))

        variables = client.kickstart.profile.getVariables(session, label)

        result[label] = {
                'label': label,
                'tree_label': p['tree_label'],
                'name': p['name'],
                'config_management': configManagement,
                'remote_commands': remoteCommands,
                'selinux': seLinux,
                'advanced_options': advancedOptions,
                'custom_options': customOptions,
                'locale': locale,
                'partitioning': partitioning,
                'keys': keys,
                'packages': packages,
                'activation_keys': activationKeys,
                'scripts': scripts,
                'variables': variables}

    return result


def exportLocalFiles(directory):
    """
    List configuration files which are local overrides for a system, for all systems
    where the "stage" custom value is set to the production stage.

    The file contents are written to the filesystem, the metadata is
    returned as a list.
    """

    result = {}

    for s in client.system.listSystems(session):
        serverId = s['id']

        if client.system.getCustomValues(session, serverId)['stage'] != STAGE3_LABEL:
            continue

        pathPrefix = directory + "/config_files_" + serverId + "/"

        # Remove any existing directory for this system, so we don't keep
        # obsolete files from a previous export.
        try:
            shutil.rmtree(pathPrefix)
        except OSError:
            pass

        # List the local configuration files for this system.
        files = client.system.config.listFiles(session, serverId, 1)
        filePaths = map(lambda f: f['path'], files)
        fileInfos = client.system.config.lookupFileInfo(session, serverId, filePaths, 1)

        for f in fileInfos:
            result[serverId] = exportFileInfos(fileInfos, pathPrefix)

    return result


def downloadConfigFiles(label, topDir):
    """
    Download the contents of a configuration channel to the filesystem,
    preserving the directory structure and filenames.
    """

    if not os.path.exists(topDir):
        os.mkdir(topDir)

    sessionFile = os.environ['HOME'] + "/.rhncfg-manager-session"
    out = open(sessionFile, 'w')
    out.write(session)
    out.close()

    cmd = "rhncfg-manager download-channel " + \
        "--topdir=" + topDir + " " + \
        "--server-name=" + SATELLITE_HOST + " " + label
    try:
        result = os.system(cmd)
        if result:
            sys.stderr.write("Error downloading configuration channel " + label + "\n" +
                             "Please run the following command to determine the cause:\n" +
                             cmd + "\n")
            sys.exit(1)
    finally:
        os.unlink(sessionFile)

        # Check if the channel was exported.
        if not os.path.exists(topDir + "/" + label):
            print "Cannot find " + topDir + "/" + label
            print "\nFailed to get config files with rhncfg-manager. Please check"
            print "that the rhncf-management package from the RHN Tools channel"
            print "is installed and that it is configured in ~/.rhncfgrc or"
            print "/etc/sysconfig/rhn/rhncfg-manager.conf like this:\n"
            print "[rhncfg-manager]"
            print "enableProxy = 0"
            print "sslCACert = /var/www/html/pub/RHN-ORG-TRUSTED-SSL-CERT"
            sys.exit(1)

def exportFileInfos(fileInfos, pathPrefix):
    """
    Write the contents of the given configuration files to the filesystem
    under "pathPrefix", and return a list with their metadata.

    At least with Satellite 5.3, this does not work for binary files,
    whose content is not returned by the configchannel.lookupFileInfo API.
    """

    result = []

    for f in fileInfos:
        path = f['path']
        type = f['type']
        binary = f['binary']

        result.append({'path': path,
                       'type': type,
                       'binary': binary,
                       'permissions': f['permissions'],
                       'owner': f['owner'],
                       'group': f['group'],
                       'macro-start-delimiter': f['macro-start-delimiter'],
                       'macro-end-delimiter': f['macro-end-delimiter']})

        # For directories, we don't need to store any file contents.
        if type == "directory":
            continue

        if binary:
            print "Cannot process binary file " + path
            sys.exit(1)

        # Determine the directory in which the file is stored.
        dir = pathPrefix + re.sub("/[^/]+$", "", path)

        try:
            os.stat(dir)
        except OSError:
            os.makedirs(dir)

        out = open(pathPrefix + path, 'w')
        out.write(f['contents'].encode('utf-8'))
        out.close()

    return result

def isBlacklisted(pkg_blacklist, pkg_details, sw_stack=None):
    """
    return True if package is blacklisted
    """
    
    service = None
    appname = None
    if sw_stack:
        (service, appname) = sw_stack.split('-')
        #TODO(not urgent): this does not work yet, have to check if it's filled before iterating
        #levels = [ 'global', service, sw_stack ]
        levels = [ 'global' ]
        for l in levels:
            if isBlacklisted(pkg_blacklist[l], pkg_details):
                return True
        return False
    else:
        name = pkg_details['name']
        version = pkg_details['version']
        release = pkg_details['release']
        epoch = pkg_details['epoch']
        if not pkg_blacklist.has_key(name):
            return False
        elif len(pkg_blacklist[name]) == 0:
            # only package name specified in blacklist
            return True
        else:
            is_blacklisted = False
            for blacklist_entry in pkg_blacklist[name]:
                if blacklist_entry.has_key('version'):
                    if blacklist_entry['version'] != version:
                        # version mismatch, not blacklisted
                        is_blacklisted = False
                        # name and version match, now check release
                    elif blacklist_entry.has_key('release'):
                        if blacklist_entry['release'] != release:
                            # release mismatch, not blacklisted
                            is_blacklisted = False
                            # name, version and release match, now check epoch
                        elif not epoch:
                            # pkg has no epoch, this is a match
                            is_blacklisted = True
                            # pkg has epoch, check it
                        elif blacklist_entry.has_key('epoch'):
                            if blacklist_entry['epoch'] != epoch:
                                # epoch mismatch, not blacklisted
                                is_blacklisted = False
                            else:
                                # name, version, release and epoch match, blacklisted
                                is_blacklisted = True
                        else:
                            # name, version and release match, package has epoch, but
                            # no epoch defined in blacklist, so it's blacklisted
                            is_blacklisted = True
                    else:
                        # name and version match, blacklisted
                        is_blacklisted = True
                                    
                else:
                    print "Warning, incorrect blacklist definition found: ", pkg_blacklist[name]
                    print "Not blacklisting package " + name
                    return False
                
                if is_blacklisted:
                    break
    
            return is_blacklisted
    
    print "Warning, Logic Error in isBlacklisted(): "
    print "Not blacklisting package " + pkg_details['name']
    return False


def exportSwChannels(stage, service, arch, directory):
    """
    Export a Software Channel defined by given stage, service (or service-app)
    and arch

    The packages are copied to a subdirectory, named with the channel label
    The file contents are written to the filesystem, the metadata is
    returned as a dict.
    
    """

    result = {}
    
    print "Exporting Software Channels"
    # read package blacklist file
    # TODO: warn if blacklist file does not exist and work with empty blacklist
    #pkg_blacklist = readJSON(PKG_BLACKLIST_FILE)
    pkg_blacklist = {'global': {}}
    if os.access(PKG_BLACKLIST_FILE, os.F_OK):
        pkg_blacklist['global'] = parseBlacklist(PKG_BLACKLIST_FILE)
    else:
        print "Not using Blacklist, File %s does not exist" % PKG_BLACKLIST_FILE
        sys.stdout.flush()
    pkg_whitelist = {'global': {}}
    if os.access(PKG_WHITELIST_FILE, os.F_OK):
        pkg_whitelist['global'] = parseBlacklist(PKG_WHITELIST_FILE)
    else:
        print "Not using Whitelist, File %s does not exist" % PKG_WHITELIST_FILE
        sys.stdout.flush()

    if service == "baseos":
        channel_rex = "^" + SW_LABEL_PREFIX + "-stage-" + stage
        if arch != 'all':
            channel_rex += "-.*" + arch
    elif service == "all":
        channel_rex = "^" + SW_LABEL_PREFIX + "-type-.*" + stage + "|" + "^" + SW_LABEL_PREFIX + "-stage-" + stage
        if arch != 'all':
            channel_rex = "^" + SW_LABEL_PREFIX + "-type-.*" + stage + "-" + arch +"|" + "^" + SW_LABEL_PREFIX + "-stage-" + stage + "-.*" + arch
    else:
        keyPrefix = "^[0-9]+-type-" + service + "(-[^-]+)?-" + stage
        channel_rex = "^" + SW_LABEL_PREFIX + "-type-" + service + "(-[^-]+)?-" + stage
        if arch != 'all':
            channel_rex += "-" + arch        
    
    #print "debug: exportSwChannels(): stage=", stage
    #print "debug: exportSwChannels(): service=", service    
    #print "debug: exportSwChannels(): arch=", arch
    
    allChannels = sorted(client.channel.listAllChannels(session),
                         lambda c1,c2: cmp(c1['label'], c2['label']))

    # determine channel labels
    #print "debug: exportSwChannels(): channel_rex=", channel_rex
    for channel in allChannels:
        channel_label = channel['label']
        m = re.match(channel_rex, channel_label)
        if m:
            exportSwChanByLabel(channel_label, directory, pkg_blacklist, pkg_whitelist, result)
            
    return result


def exportSwChanByLabel(channel_label, directory, pkg_blacklist, pkg_whitelist, result):
    """
    export a software channel specified by given channel label
    """
    
    print "Exporting Channel " + channel_label
    sys.stdout.flush()
    result[channel_label] = {}
    pathPrefix = directory + "/software_channels/" + channel_label
    packagesPrefix = pathPrefix + "/packages"

    # Remove any existing directory for this channel, so we don't keep
    # obsolete files from a previous export.
    try:
        shutil.rmtree(pathPrefix)
    except OSError:
        pass

    try:
        os.stat(packagesPrefix)
    except OSError:
        os.makedirs(packagesPrefix)

    channel_details = client.channel.software.getDetails(session, channel_label)
    result[channel_label]['channel_details'] = channel_details

    all_pkgs = None
    try:
        all_pkgs = client.channel.software.listAllPackages(session, channel_label)
    except xmlrpclib.Fault, err:
        print "An error has occured:"
        print "Fault code: %d" % err.faultCode
        print "Fault string: %s" % err.faultString
    except xmlrpclib.ProtocolError, err:
        print "An error has occured:"
        print "Error code: %d" % err.errcode
        print "Error message: %s" % err.errmsg

    if all_pkgs == None:
        print "Error getting package list for channel " + channel_label + ". Aborting"
        sys.exit(1)
    
    result[channel_label]['all_packages'] = all_pkgs

    result[channel_label]['pkg_details'] = {}

    # need to remove them later from result before returning it
    blacklisted_pkg_ids = []

    for pkg in all_pkgs:
        pkg_details = client.packages.getDetails(session, pkg['id'])
        pretty_pkg_name = getPrintablePkgName(pkg_details)
        if pkg_whitelist['global']:
            # a whitelist is defined, only include whitelisted packages
            if isBlacklisted(pkg_whitelist['global'], pkg_details):
                print "including whitelisted package " + pretty_pkg_name
                sys.stdout.flush()
            else:
                blacklisted_pkg_ids.append(pkg_details['id'])
                print "excluding non-whitelisted package " + pretty_pkg_name
                sys.stdout.flush()
                continue
        if isBlacklisted(pkg_blacklist['global'], pkg_details):
            blacklisted_pkg_ids.append(pkg_details['id'])
            print "skipping blacklisted package " + pretty_pkg_name
            sys.stdout.flush()
            continue
        else:
            print "exporting package " + pretty_pkg_name
            sys.stdout.flush()
                
        src_path = pkg_details['path']
        dst_path = packagesPrefix + '/' + src_path
        # Determine the destination directory to which the file will be copied
        dst_dir = re.sub("/[^/]+$", "", dst_path)

        try:
            os.stat(dst_dir)
        except OSError:
            os.makedirs(dst_dir)
        try:
            shutil.copyfile(SW_CHANNEL_STORE_PREFIX + '/' + src_path, dst_path)
            result[channel_label]['pkg_details'][pkg['id']] = pkg_details
        except (IOError, os.error), why:
            print "Can't copy %s to %s: %s" % (`src_path`, `dst_path`, str(why))
            sys.stdout.flush()
    
    # remove blacklisted pkgs from result
    pkg_ids = map(lambda f: f['id'], result[channel_label]['all_packages'])
    for id in blacklisted_pkg_ids:
        i = pkg_ids.index(id)
        del result[channel_label]['all_packages'][i]
        del pkg_ids[i]

    # export Errata
    errata = exportErrataByChan(channel_label)
    result[channel_label]['errata'] = errata

    return result

def getPrintablePkgName(pkg_details):
    """
    Returns a Package Name for printing
    """
    pretty_pkg_name = ''
    if pkg_details['epoch']:
        pretty_pkg_name = "%s-%s-%s:%s.%s.rpm" % (pkg_details['name'],
                                                  pkg_details['version'],
                                                  pkg_details['release'],
                                                  pkg_details['epoch'],
                                                  pkg_details['arch_label'])
    else:
        pretty_pkg_name = "%s-%s-%s.%s.rpm" % (pkg_details['name'],
                                               pkg_details['version'],
                                               pkg_details['release'],
                                               pkg_details['arch_label'])

    return pretty_pkg_name

def exportErrataByChan(channel_label):
    """
    Export custom Errata for a given Channel label
    """
    
    result = []
    
    try:
        errata = client.channel.software.listErrata(session, channel_label)
        for erratum in errata:
            advisory_name = erratum['advisory_name']
            details = client.errata.getDetails(session, advisory_name)
            # errata.create and errata.setDetails expect buglist as an array
            bugzillaFixes_tmp = client.errata.bugzillaFixes(session, advisory_name)
            bugzillaFixes = []
            for bug in bugzillaFixes_tmp:
                bugzillaFixes.append({'id': int(bug), 'summary': bugzillaFixes_tmp[bug]})
            keywords = client.errata.listKeywords(session, advisory_name)
            packages = client.errata.listPackages(session, advisory_name)
            
            result.append({
                           'advisory_name': advisory_name,
                           'details': details,
                           'bugzilla_fixes': bugzillaFixes,
                           'keywords': keywords,
                           'packages': packages})

    except xmlrpclib.Fault, err:
        print "An error has occured:"
        print "Fault code: %d" % err.faultCode
        print "Fault string: %s" % err.faultString
    except xmlrpclib.ProtocolError, err:
        print "An error has occured:"
        print "Error code: %d" % err.errcode
        print "Error message: %s" % err.errmsg
    
    return result


def getNextStage(stage):
    """
    returns the next stage for a given stage
    """
    stages = [ STAGE1_LABEL, STAGE2_LABEL, STAGE3_LABEL]
    return stages[stages.index(stage)+1]

def getSWChannelTree():
    """
    returns a dict of all software channels representing the base/child channel tree
    """

    channel_tree = {}
    all_channels = client.channel.listAllChannels(session)
    for chan in all_channels:
        channel_details = client.channel.software.getDetails(session, chan['label'])
        if channel_details['parent_channel_label']:
            parent_label = channel_details['parent_channel_label']
            if parent_label not in channel_tree:
                channel_tree[parent_label] = []
            channel_tree[parent_label].append(chan['label'])

    return channel_tree

def mergeSWChannels(stage, arch, interactive):
    """
    Calls mergeSWChannel for one or multiple base channels if applicable
    """

    # If we are to merge from the first lifecycle stage, list all Red Hat
    # base channels. Otherwise, list all cloned base channels of the given
    # lifecycle stage.

    result = {}
    if stage == STAGE1_LABEL:
        if arch == 'all':
            basePattern = "^rhel-"
        else:
            basePattern = "^rhel-" + arch
        targetReplace = "^"
    else:
        if arch == 'all':
            basePattern = SW_CLONE_PREFIX + '-' + stage + '-rhel-'
        else:
            basePattern = SW_CLONE_PREFIX + '-' + stage + '-rhel-' + arch
        targetReplace = SW_CLONE_PREFIX + '-' + stage + '-'

    next_stage = getNextStage(stage)
    channel_tree = getSWChannelTree()

    for base_channel in channel_tree:
        if re.match(basePattern, base_channel):
            targetChannel = re.sub(targetReplace, 
                                   SW_CLONE_PREFIX + '-' + next_stage + '-', 
                                   base_channel)

            # Only process base channels which have a clone in the next
            # lifecycle stage. If the "interactive" flag is set, ask the
            # user if the base channel should be processed.
            if targetChannel in channel_tree:
                c = 'y'
                if interactive:
                    print "************************************************************************"
                    c = getch("\nProcess " + base_channel + " and child channels (Y/n)?")

                if c == 'y' or c == '':
                    result[targetChannel] = \
                        mergeSWChannel(stage, base_channel, interactive)[targetChannel]
    
    return result

def mergeSWChannel(srcStage, srcBaseChannel, interactive):
    """
    Merge errata and packages from a given base software channel and its
    child channels into the corresponding channels of the next stage in the
    release cycle.

    Assumptions: srcBaseChannel is a base SW Channel label eg. rhel-i386-server-5 or
    clone-test-rhel-i386-server-5.
    
    Returns a dict of merged channels (key: target base channel, value: list of target
    child channels. Used for calling rhn-satellite-exporter afterwards.
    """

    channel_tree = getSWChannelTree()

    # Determine which part of the source label we'll have to replace to get
    # the target label (with the new target stage).
    if srcStage == STAGE1_LABEL:
        targetReplace = '^'
    else:
        targetReplace = '^' + SW_CLONE_PREFIX + '-' + srcStage + '-'

    tgtStage = getNextStage(srcStage)

    tgtBaseChannel = re.sub(targetReplace,
                         SW_CLONE_PREFIX + '-' + tgtStage + '-', 
                         srcBaseChannel)

    print
    print "Stage: " + srcStage + ' -> ' + tgtStage
    print "Base:  " + srcBaseChannel + ' -> ' + tgtBaseChannel

    sw_channel_stage_map = {}
    sw_channel_stage_map[srcBaseChannel] = tgtBaseChannel
    merged_channels = {}
    merged_channels[tgtBaseChannel] = []

    # First determine the source and target child channels which we will
    # have to process in the next step.
    for child_channel in channel_tree[srcBaseChannel]:
        # For some setups, we only want to merge the RHN Tools child
        # channel. If all child channels should be included, the
        # baseos_chans_rh_rex parameter in /etc/sysconfig/rhof 
        # can be set to ".*"
        if not re.match(BASEOS_CHANS_RH_REX, child_channel):
            continue

        # For custom child channels, we keep the prefix, and only replace
        # the lifecycle stage name. Otherwise, we prepend the
        # SW_CLONE_PREFIX. Strictly speaking, this is only necessary when we
        # are merging from the Red Hat channels to the second lifecycle
        # stage.
        if re.match('^' + SW_LABEL_PREFIX, child_channel):
            tgtChildChannel = changeLabelStage(child_channel, tgtStage)
        else:
            tgtChildChannel = re.sub(targetReplace,
                                     SW_CLONE_PREFIX + '-' + tgtStage + '-',
                                     child_channel)

        # Check if the child channel exists under the target base
        # channel. If not, we skip it.
        if tgtChildChannel in channel_tree[tgtBaseChannel]:
            sw_channel_stage_map[child_channel] = tgtChildChannel
            merged_channels[tgtBaseChannel].append(tgtChildChannel)

    for src_channel_label in sw_channel_stage_map:
        c = 'y'
        if interactive:
            c = getch("\nCopy " +src_channel_label  + " errata and packages (Y/n)?")

        if c != 'y' and c != '':
            continue
            
        print '\n' + src_channel_label + ' -> ' + sw_channel_stage_map[src_channel_label]

        merged_errata = client.channel.software.mergeErrata(session,
                                                            src_channel_label,
                                                            sw_channel_stage_map[src_channel_label])

        if merged_errata:
            print "Merged errata:"
            for erratum in merged_errata:
                print "%s %s %s %s" % (erratum['date'], 
                                       erratum['advisory_name'], 
                                       erratum['advisory_type'], 
                                       erratum['advisory_synopsis'])
        print "Merging errata in the background: " + str(len(merged_errata))

        try:
            merged_packages = []
            merged_packages = \
                client.channel.software.mergePackages(session, 
                                                      src_channel_label, 
                                                      sw_channel_stage_map[src_channel_label])
        except xmlrpclib.Fault, err:
            print "An error has occured:"
            print "Fault code: %d" % err.faultCode
            print "Fault string: %s" % err.faultString
        except xmlrpclib.ProtocolError, err:
            print "An error has occured:"
            print "Error code: %d" % err.errcode
            print "Error message: %s" % err.errmsg
            
        print "Merged packages: " + str(len(merged_packages))
        
    return merged_channels

def runSatExporter(merged_tgt_channels, directory):
    """
    run rhn-satellite-exporter for exporting the channels merged by mergeSWChannel.
    """
    
    # rhn-satellite-exporter caches errata XML files in
    # /var/cache/rhn/xml-errata. As of 2010-08-25, this cache is not updated
    # after we merge errata from one channel into another, which gives us
    # the wrong list of channels for the errata in our export
    # (https://bugzilla.redhat.com/show_bug.cgi?id=620486). As a workaround,
    # we delete the cache before running rhn-satellite-exporter.

    shutil.rmtree('/var/cache/rhn/xml-errata', True)

    for base_channel in merged_tgt_channels:
        channel_list = [base_channel]
        channel_list.extend(merged_tgt_channels[base_channel])
        tgt_dir = directory + '/rhn-sat-export/' + base_channel
        try:
            os.stat(tgt_dir)
        except OSError:
            os.makedirs(tgt_dir)
        
        satexporter_cmd = 'rhn-satellite-exporter --dir=' + tgt_dir
        satexporter_cmd += ' --verbose --print-report --hard-links'
        for c in channel_list:
            satexporter_cmd += ' --channel=' + c
        
        print 'Running ' + satexporter_cmd
        print '(This can take some hours ...)'
        sys.stdout.flush()
        (satexporter_status, satexporter_output) = commands.getstatusoutput(satexporter_cmd)
        print "Output:"
        print satexporter_output
        sys.stdout.flush()
        
def getErrataLists(merged_channels):
    """
    Returns the lists of Errata advisory names for the channels given
    This is needed as a workaround because rhn-sat-exporter does not export the
    complete list of channels, so that satellite-sync can not import errata correctly
    see https://bugzilla.redhat.com/show_bug.cgi?id=620486
    """
    errata_lists = {}
    channel_list = []
    for base_channel in merged_channels:
        channel_list.append(base_channel)
        channel_list.extend(merged_channels[base_channel])
    
    for channel in channel_list:
        errata = client.channel.software.listErrata(session, channel)
        errata_lists[channel] = map(lambda e: e['advisory_name'], errata)

    return errata_lists

def dumpJSON(filename, data):
    """
    Write a Python data structure in JSON format to the given file.
    """

    out = open(filename, 'w')
    out.write(json.dumps(data, sort_keys=True, indent=2))
    out.close()

def readJSON(filename):
    """
    Read the given JSON file and return its contents as a Python data
    structure.
    """

    jsonIn = open(filename, 'r')
    result = json.load(jsonIn)
    jsonIn.close()

    return result
        
def addToBlacklist(blacklist, m, attrs):
    """
    add data from match to blacklist structure
    """
    if not blacklist.has_key(m.group('name')):
        blacklist[m.group('name')] = []
    
    blacklist_entry = {}
    for a in attrs:
        blacklist_entry[a] = m.group(a)
        
    blacklist[m.group('name')].append(blacklist_entry)

def parseBlacklist(filename):
    """
    Parse Blacklist File
    
    Assumptions:
    - name:
      - may contain multiple -
      - may contain version numbers
    - version:
      - starts with digit or contains digit(s)
      - never contains -
    - release:
      - always starts with digit
      - never contains -
    - epoch:
      - always one or more digit(s)
    """

    p_n = r"^(?P<name>.+)$"
    p_nv = r"^(?P<name>.+) (?P<version>\d[^-]*|\w+\d[^-]*)$"
    p_na = r"^(?P<name>.+)\.(?P<arch>i386|x86_64|noarch)$"
    p_nvr = r"^(?P<name>.+) (?P<version>\d[^-]*|\w+\d[^-]*) (?P<release>\d[^-]*)$"
    p_nvra = r"^(?P<name>.+) (?P<version>\d[^-]*|\w+\d[^-]*) (?P<release>\d[^-]*)\.(?P<arch>i386|x86_64|noarch)$"
    p_nvre = r"^(?P<name>.+) (?P<version>\d[^-]*|\w+\d[^-]*) (?P<release>\d[^-]*):(?P<epoch>\d+)$"
    p_nvrea = r"^(?P<name>.+) (?P<version>\d[^-]*|\w+\d[^-]*) (?P<release>\d[^-]*):(?P<epoch>\d+)\.(?P<arch>i386|x86_64|noarch)$"

    p_comment_re = re.compile(r"^#")
    p_n_re = re.compile(p_n)
    p_nv_re = re.compile(p_nv)
    p_na_re = re.compile(p_na)
    p_nvr_re = re.compile(p_nvr)
    p_nvra_re = re.compile(p_nvra)
    p_nvre_re = re.compile(p_nvre)
    p_nvrea_re = re.compile(p_nvrea)
    
    blacklist = {}
    blf = open(filename, 'r')
    lines = blf.readlines()
    blf.close()
    for l in lines:
        l = l.strip()

        if p_comment_re.match(l):
            continue

        m = p_nvrea_re.match(l)
        if m:
            print "[nvrea]: name: %s version: %s release: %s epoch: %s arch: %s" % (m.group('name'), m.group('version'), m.group('release'), m.group('epoch'), m.group('arch'))
            addToBlacklist(blacklist, m, ['version','release','epoch','arch'])
            continue
        m = p_nvre_re.match(l)
        if m:
            print "[nvre]:  name: %s version: %s release: %s epoch: %s" % (m.group('name'), m.group('version'), m.group('release'), m.group('epoch'))
            addToBlacklist(blacklist, m, ['version','release','epoch'])
            continue
        m = p_nvra_re.match(l)
        if m:
            print "[nvra]:  name: %s version: %s release: %s arch: %s" % (m.group('name'), m.group('version'), m.group('release'), m.group('arch'))
            addToBlacklist(blacklist, m, ['version','release','arch'])
            continue
        m = p_nvr_re.match(l)
        if m:
            print "[nvr]:  name: %s version: %s release: %s" % (m.group('name'), m.group('version'), m.group('release'))
            addToBlacklist(blacklist, m, ['version','release'])
            continue
        m = p_nv_re.match(l)
        if m:
            print "[nv]:  name: %s version: %s" % (m.group('name'), m.group('version'))
            addToBlacklist(blacklist, m, ['version'])
            continue
        m = p_na_re.match(l)
        if m:
            print "[na]:  name: %s arch: %s" % (m.group('name'), m.group('arch'))
            addToBlacklist(blacklist, m, ['arch'])
            continue
        m = p_n_re.match(l)
        if m:
            print "[n]:  name: %s" % (m.group('name'))
            blacklist[m.group('name')] = []
            
    return blacklist

def changeLabelStage(label, tgtStage):
    """
    Replace the lifecycle stage in the given label with the target stage.
    """

    return re.sub("(-|^)(" + STAGE1_LABEL + "|" + STAGE2_LABEL + "|" + STAGE3_LABEL + ")(-|$)",
                  r"\1" + tgtStage + r"\3", label)

def mkdir(directory_name):
    """
    Utility Function for creating directories
    """
    try:
        os.stat(directory_name)
    except OSError:
        os.makedirs(directory_name)

def getch(prompt):
    """
    Read a single character from STDIN, so users can control the script 
    with a single keypress.
    """
    print prompt + ' ',

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    # Check for Ctrl+C
    if ord(ch) == 3:
        sys.exit("Exiting on user cancel")

    # If the user pressed Enter, return an empty string.
    if ch == "\r":
        ch = ''

    print ch
    return ch

if __name__ == "__main__":
    main()
