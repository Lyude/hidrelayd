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

import configparser
import os
from usb_gadget import UsbGadget, UsbProtocolVersion

class DaemonConfig(configparser.ConfigParser):
    DEFAULTS = {
        'debug': False,
    }
    GADGET_DEFAULTS = {
        'has_keyboard': True,
        'has_mouse':    True,
        'usb_version':  1.1,
        'vendor_id':    0xa4ac,
        'product_id':   0x0525,
        'serial':       '1337beef',
        'manufacturer': 'hidrelayd',
        'product':      'Remote HID device'
    }

    def __init__(self):
        super().__init__()

    def _read(self, f, fpname):
        super()._read(f, fpname)

        # Load configuration defaults
        if not self.has_section('hidrelayd'):
            self.add_section('hidrelayd')
        for option in self.DEFAULTS:
            if not self.has_option('hidrelayd', option):
                self.set('hidrelayd', option, str(self.DEFAULTS[option]))

        has_at_least_one_gadget = False

        for section in self.sections():
            if section.startswith("gadget:"):
                has_at_least_one_gadget = True

                gadget_name = section.split(":")[1]
                if gadget_name == "":
                    raise configparser.Error(
                        "Empty gadget name for section %s" % section)

                for option in self.GADGET_DEFAULTS:
                    if not self.has_option(section, option):
                        self.set(section, option,
                                 str(self.GADGET_DEFAULTS[option]))

                # We can't have a gadget configuration with no devices
                if self.getboolean(section, 'has_keyboard') == False and \
                   self.getboolean(section, 'has_mouse') == False:
                    raise configparser.Error(
                        "Gadget '%s' must have at least one mouse or keyboard" %
                        gadget_name)

            elif section != "hidrelayd":
                raise configparser.Error("Unknown section '%s'" % section)

        if not has_at_least_one_gadget:
            raise configparser.Error(
                "Must have at least one USB gadget specified in the config")

    def get_usb_version(self, section):
        """
        Parse and validate the USB version for a gadget configuration section
        """
        try:
            major, minor = self.get(section, 'usb_version').split(".")
            usb_version = UsbProtocolVersion['USB_%s_%s' % (major, minor)]
        except Exception:
            raise configparser.Error(
                "Invalid USB protocol revision '%s' in section '%s'" % (
                    version_str, section))

        return usb_version
