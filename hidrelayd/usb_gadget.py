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

import os
import sys
import errno
import pyudev
import weakref
import fcntl
import functools
from enum import Enum
from logging import debug, info, error
from itertools import count

class ConfigfsDir():
    def __init__(self, path, is_child=False):
        """
        This is a configfs helper that helps with automatic cleanup of the sysfs
        directories and links that we make by removing them from most recently
        created to least recently created (so as not to make kernel drivers
        complain)
        """
        self.path = path
        self.__keep_alive = list()
        self.__child_dirs = list()
        self.__child_links = list()
        self.__extra_cleanup_cbs = list()
        os.mkdir(self.path)

        # Ensures directories always get cleaned up on GC
        def cleanup_cb(path, child_dirs, child_links, extra_cleanup_cbs):
            debug("%s: calling extra cleanup callbacks" % path)
            for cb, args, kw_args in extra_cleanup_cbs:
                cb(*args, **kw_args)

            debug("%s: removing links" % path)
            for finalizer in child_links:
                finalizer()

            debug("%s: removing children" % path)
            for finalizer in child_dirs:
                finalizer()

            debug("%s: removing self" % path)
            os.rmdir(self.path)

        """
        Guarantees that all of the configfs directories created by this object
        have been removed. A ConfigfsDir object cannot be used after this has
        been called.

        When deleting a ConfigfsDir object (or objects inheriting this class),
        this method should ALWAYS be called beforehand to ensure that
        directories actually get cleaned up, since a ConfigfsDir object might
        stay alive beyond the current scope even with deletion.
        """
        self.close = weakref.finalize(self, cleanup_cb,
                                      self.path,
                                      self.__child_dirs,
                                      self.__child_links,
                                      self.__extra_cleanup_cbs)

        # Top-level parents are responsible for invoking their children's
        # finalizers before destroying theirselves. This ensures we -always-
        # end up removing directories/links from the bottom up
        if is_child:
            self.close.atexit = False

    def _register_cleanup_cb(self, cb, *args, **kwargs):
        self.__extra_cleanup_cbs.append(tuple([cb, args, kwargs]))

    def _set(self, path, value):
        if isinstance(value, str):
            debug('%s: "%s" -> %s' % (self.path, value, path))

        with open(self.path + '/' + path,
                  mode='wb' if isinstance(value, bytes) else 'w') as attr:
            attr.write(value)

    def _get(self, path):
        with open(self.path + '/' + path) as attr:
            val = attr.read().strip()
            debug('%s: "%s" <- %s' % (self.path, val, path))
            return val

    def _mkdir(self, path, keep_ref=True):
        """
        Create a directory inside this object's location.

        Keyword arguments:
        keep_ref -- Whether the directory stays alive until self is destroyed
        """
        debug('%s: mkdir %s' % (self.path, path))

        new_dir = ConfigfsDir('%s/%s' % (self.path, path), True)
        if keep_ref:
            self.__keep_alive.append(new_dir)

        self.__child_dirs.append(new_dir.close)
        return new_dir

    def _link(self, name, dest):
        """
        Create a link to another ConfigfsDir object inside this one. If the
        object is destroyed before self, it's link is automatically removed.
        """
        debug('%s: %s -> %s' % (self.path, name, dest.path))
        os.symlink(dest.path, self.path + '/' + name)

        def link_cleanup_cb(link_path):
            os.remove(link_path)

        self.__child_links.append(weakref.finalize(dest, link_cleanup_cb,
                                                   self.path + '/' + name))

class UsbGadget(ConfigfsDir):
    """
    A USB HID Gadget, created through the Linux kernel's USB gadget configfs
    interface. A single gadget can serve multiple functions at the same time,
    such as acting as both a keyboard and a mouse.

    Keyword arguments:
    name -- The name to give the Gadget (not shown to the host)
    version -- The USB protocol version to use
    vendor_id -- The vendor ID of the gadget, assigned by the USB Group
    product_id -- The product ID of the gadget, assigned by the USB Group
    serial -- A string containing the serial number of the gadget
    manufacturer -- A string containing the name of the manufacturer for the
                    gadget
    product -- A string containing the product name for the gadget
    """
    class ProtocolVersion(Enum):
        """ A set of enumerators for each USB protocol revision """
        USB_1_0 = 0x0100
        USB_1_1 = 0x0110
        USB_2_0 = 0x0200

    class Exception(Exception):
        pass

    def __init__(self, name,
                 version=ProtocolVersion.USB_1_1,
                 vendor_id=0xa4ac, product_id=0x0525,
                 serial='', manufacturer='Lyude',
                 product='Wolf powered HID gadget'):
        assert version in UsbGadget.ProtocolVersion
        assert isinstance(serial, str)
        assert isinstance(manufacturer, str)
        assert isinstance(product, str)

        self.name = name
        super().__init__('/sys/kernel/config/usb_gadget/' + name)

        """ The serial number string for the USB gadget """
        self.serial = serial
        """ The manufacturer string for the USB gadget """
        self.manufacturer = manufacturer
        """ The product string for the USB gadget """
        self.product = product

        self.bound = False

        self._function_id = count(start=1)
        self._bound_devs = list()

        self._set('idVendor', hex(vendor_id))
        self._set('idProduct', hex(product_id))
        self._set('bcdUSB', hex(version.value))

        strings = self._mkdir('strings/0x409')
        strings._set('serialnumber', serial)
        strings._set('manufacturer', manufacturer)
        strings._set('product', product)

        # Create the main config to use for USB hid functions
        gadget_config = self._mkdir('configs/c.1')
        config_strings = gadget_config._mkdir('strings/0x409')
        config_strings._set('configuration', 'Configuration 1')

        self._gadget_config = gadget_config

        # Make sure we unbind our UDC device before getting GCd
        def unbind_cleanup_cb(bound_devs, udc_ctl):
            for dev in bound_devs:
                dev.close()
            bound_devs.clear()

            try:
                with open(udc_ctl, 'w') as udc_ctl_fd:
                    udc_ctl_fd.write('\n')
            except Exception:
                pass

        self._register_cleanup_cb(unbind_cleanup_cb, self._bound_devs,
                                  self.path + '/UDC')

    def create_function(self, protocol, report_length, report_descriptor):
        function_name = 'hid.usb%d' % next(self._function_id)

        function = self._mkdir('functions/%s' % function_name, keep_ref=False)
        function._set('protocol', str(protocol))
        function._set('report_length', str(report_length))
        function._set('report_desc', bytes(report_descriptor))
        function._set('subclass', '1')
        self._gadget_config._link(function_name, function)

        return function

    def find_hidg_device(self, function):
        device_number = os.makedev(*[int(n) for n in
                                     function._get('dev').split(':')])
        device = pyudev.Devices.from_device_number(pyudev.Context(), 'char',
                                                   device_number)
        char_dev = open(device.device_node, 'wb')

        self._bound_devs.append(char_dev)
        return char_dev

    def bind(self, udc_dev):
        info('Binding %s to %s' % (self.name, udc_dev))
        try:
            self._set('UDC', udc_dev)
        except OSError as e:
            if e.errno == errno.ENODEV:
                raise UsbGadget.Exception('No HID devices added to gadget')
            else:
                raise e

        self.bound = True

    def unbind(self):
        debug('Unbinding %s' % self.name)
        # Drop any hidg nodes that depended on this binding
        for dev in self._bound_devs:
            dev.close()

        self._set('UDC', '\n')
        self.bound = False

        self._bound_devs.clear()
