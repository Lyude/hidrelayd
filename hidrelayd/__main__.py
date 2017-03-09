#!/usr/bin/python3

import argparse
import logging
from logging import info, debug, error
from sys import stdout, exit
from kmod import Kmod

parser = argparse.ArgumentParser(
    description="Relay daemon for remotely controllable USB HID devices"
)
parser.add_argument('-v', '--verbose', help='Show debugging messages',
                    action="store_true")
parser.add_argument('-c', '--config', help='Load a specific configuration file',
                    type=argparse.FileType())
args = parser.parse_args()

if args.verbose:
    logging.Logger.setLevel(logging.DEBUG)

if args.config:
    config = args.config
else:
    try:
        config = open('/etc/hidrelayd.conf')
    except Exception as e:
        error("Failed to open config file /etc/hidrelayd.conf: %s" % e.msg)
        exit(1)

kmod = Kmod()
libcomposite = km.module_from_name('libcomposite')
if libcomposite.refcnt > 0:
    debug('libcomposite already loaded, skipping')
else:
    debug('Loading libcomposite...')
    km.modprobe('libcomposite')
