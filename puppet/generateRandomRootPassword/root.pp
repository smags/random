# == Class: xxx::root
#
# this class sets the root password
#
# === Parameters
#
# $is_disabled
#   enable or disable this module.
#   allowed values: true / false
#
# $password
#   overrides the password with a pre encrypted password
#   if set it disables all other automatic password algorythms
#   for a system
#
# === Variables
#
# === Examples
#
# === Authors
#
class xxx::root($stage = 'os-pre', $is_disabled = false, $password = 'notset',) {
 if $password == 'notset' {
      user {'root':
        ensure          => 'present',
        forcelocal      => true,
        comment         => 'the master of all and nothing',
        gid             => '0',
        home            => '/root',
        # An automatic random password will be set with the following line:
        password        => generate('/bin/genpass.py', $fqdn),
        shell           => '/bin/bash',
        uid             => '0',
      }

 }
 else {
      # use password entry from foreman
      user {'root':
        ensure         => 'present',
        forcelocal     => true,
        comment        => 'the master of all and nothing',
        gid            => '0',
        home           => '/root',
        password       => $password,
        shell          => '/bin/bash',
        uid            => '0',
      }
  }
} # close class


