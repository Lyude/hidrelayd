#!/usr/bin/python3
# hidrelayd - A daemon for powering remotely controllable HID devices
#
# Copyright (C) 2017 Red Hat Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA  02110-1301, USA.
#
# Authors:
#   Lyude Paul <lyude@redhat.com> (or thatslyude@gmail.com)

import argparse
import logging
from logging import info, debug, error
from sys import stdout, exit
from kmod import Kmod

from relay_device import *
from config import DaemonConfig

parser = argparse.ArgumentParser(
    description="Relay daemon for remotely controllable USB HID devices"
)
parser.add_argument('-v', '--verbose', help='Show debugging messages',
                    action="store_true")
parser.add_argument('-c', '--config', help='Load a specific configuration file',
                    default='/etc/hidrelayd.conf')
args = parser.parse_args()

config = DaemonConfig()
try:
    config.read_file(open(args.config), args.config)
except OSError as e:
    error("Failed to read config file '%s': %s" % (args.config, e.strerror))
    exit(1)

if config.getboolean('hidrelayd', 'debug') or args.verbose:
    logging.basicConfig(level=logging.DEBUG)

km = Kmod()
libcomposite = km.module_from_name('libcomposite')
if libcomposite.refcnt > 0:
    debug('libcomposite already loaded, skipping')
else:
    debug('Loading libcomposite...')
    km.modprobe('libcomposite')

debug('Initializing relay devices...')
devices = []
for section in config.sections():
    if not section.startswith("gadget:"):
        continue

    devices.append(RelayDevice(section, config))

print("Can't do much past this point just yet, but all of the devices should be ready!")
input()
