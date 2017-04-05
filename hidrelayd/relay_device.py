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

from logging import debug
from usb_gadget import UsbGadget
from ghid import *

class RelayDevice():
    """
    The toplevel object for HID relay devices
    """
    def __init__(self, section, daemon_config):
        self.gadget = UsbGadget(
            name=section.split(':')[1],
            version=daemon_config.get_usb_version(section),
            vendor_id=daemon_config.getint(section, 'vendor_id'),
            product_id=daemon_config.getint(section, 'product_id'),
            serial=daemon_config.get(section, 'serial'),
            manufacturer=daemon_config.get(section, 'manufacturer'),
            product=daemon_config.get(section, 'product')
        )

        if daemon_config.get(section, 'has_keyboard'):
            self.keyboard = Keyboard(self.gadget)
        else:
            self.keyboard = None

        if daemon_config.get(section, 'has_mouse'):
            self.mouse = Mouse(self.gadget)
        else:
            self.mouse = None

        self.gadget.bind(daemon_config.get(section, 'udc_device'))
