#!/usr/bin/python3

import os
import errno
from time import sleep
from enum import Enum
from logging import debug, info, error

class ConfigfsDir():
    def __init__(self, path):
        """
        This is a configfs helper that helps with automatic cleanup of the sysfs
        directories and links that we make by removing them from most recently
        created to least recently created (so as not to make kernel drivers
        complain)
        """
        self.path = path
        self._child_dirs = list()
        self._child_links = list()
        os.mkdir(self.path)

    def _set(self, path, value):
        if isinstance(value, str):
            debug('"%s" -> %s' % (path, value))

        with open(self.path + '/' + path,
                  mode='wb' if isinstance(value, bytes) else 'w') as attr:
            attr.write(value)

    def _mkdir(self, path):
        new_dir = ConfigfsDir('%s/%s' % (self.path, path))
        self._child_dirs.append(new_dir)
        return new_dir

    def _symlink(self, src, dest):
        full_dest = '%s/%s' % (self.path, dest)
        new_link = os.symlink(src, full_dest)
        self._child_links.append(full_dest)

    def _rmlink(self, path):
        assert os.path.islink(dest)
        self._child_links.remove(dest)
        os.remove(dest)

    def __del__(self):
        debug("Cleaning up %s" % self.path)
        for link in self._child_links:
            os.remove(link)

        del self._child_dirs
        os.rmdir(self.path)

class HidGadget(ConfigfsDir):
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
    configfs_mount -- Where the kernel's configfs filesystem is mounted
    """
    class ProtocolVersion(Enum):
        """ A set of enumerators for each USB protocol revision """
        USB_1_0 = 0x0100
        USB_1_1 = 0x0110
        USB_2_0 = 0x0200

    class Exception(Exception):
        pass

    # We may get rid of this
    class _Function(ConfigfsDir):
        REPORT_LEN = 8
        USB_CLASS = 3
        USB_SUBCLASS = 1

        KEYBOARD_DESCRIPTOR = bytes([
            0x05, 0x01, 0x09, 0x06, 0xa1, 0x01, 0x05, 0x07, 0x19, 0xe0, 0x29,
            0xe7, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
            0x95, 0x01, 0x75, 0x08, 0x81, 0x03, 0x95, 0x05, 0x75, 0x01, 0x05,
            0x08, 0x19, 0x01, 0x29, 0x05, 0x91, 0x02, 0x95, 0x01, 0x75, 0x03,
            0x91, 0x03, 0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05,
            0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xc0
        ])

        class Protocol(Enum):
            KEYBOARD = 1
            MOUSE = 2

        def __init__(self, gadget, id, protocol, report_descriptor):
            self.gadget = gadget
            self.name = 'hid.usb%d' % id
            super().__init__('%s/functions/%s' % (gadget.path, self.name))

            self._set('protocol', str(protocol.value))
            self._set('report_length', str(self.REPORT_LEN))
            self._set('report_desc', bytes(report_descriptor))
            self._set('subclass', str(self.USB_SUBCLASS))

    class _Config(ConfigfsDir):
        MAX_POWER = 120 # mA

        def __init__(self, gadget, id):
            self.gadget = gadget
            self.name = 'c.%d' % id
            super().__init__('%s/configs/%s' % (gadget.path, self.name))

            self._set('MaxPower', str(self.MAX_POWER))
            strings = self._mkdir('strings/0x409')
            strings._set('configuration', 'Configuration %d' % id)

        def add_function(self, function):
            self._symlink(function.path, function.name)

        def remove_function(self, function):
            self._rmlink(function.name)

    def __init__(self, name,
                 version=ProtocolVersion.USB_1_1,
                 vendor_id=0xa4ac, product_id=0x0525,
                 serial='', manufacturer='Lyude',
                 product='Wolf powered HID gadget'):
        assert version in HidGadget.ProtocolVersion
        assert isinstance(serial, str)
        assert isinstance(manufacturer, str)
        assert isinstance(product, str)

        self.name = name
        super().__init__('/sys/kernel/config/usb_gadget/' + name)

        self._configs = list()

        """ The serial number string for the USB gadget """
        self.serial = serial
        """ The manufacturer string for the USB gadget """
        self.manufacturer = manufacturer
        """ The product string for the USB gadget """
        self.product = product

        self.__bound = False

        self._set('idVendor', hex(vendor_id))
        self._set('idProduct', hex(product_id))
        self._set('bcdUSB', hex(version.value))

        strings = self._mkdir('strings/0x409')
        strings._set('serialnumber', serial)
        strings._set('manufacturer', manufacturer)
        strings._set('product', product)

        self.__kbd_config = HidGadget._Config(self, 1)
        self.__kbd_function = HidGadget._Function(
            self, 1, HidGadget._Function.Protocol.KEYBOARD,
            HidGadget._Function.KEYBOARD_DESCRIPTOR)
        self.__kbd_config.add_function(self.__kbd_function)

    def bind(self, udc_dev):
        """
        Bind the USB Gadget configuration to a UDC device (e.g. an OTG port)

        Keyword arguments:
        udc_dev -- The UDC device in /sys/class/udc to bind to
        """
        assert not self.__bound

        info('Binding %s to %s' % (self.name, udc_dev))
        try:
            self._set('UDC', udc_dev)
        except OSError as e:
            if e.errno == ENODEV:
                raise UsbGadget.Exception('No HID devices added to gadget')
            else:
                raise e
        self.__bound = True

    def unbind(self):
        """ Unbind the USB Gadget configuration from a UDC device """
        assert self.__bound

        info('Unbinding %s' % self.name)
        self._set('UDC', '\n')
        self.__bound = False

    def __del__(self):
        try:
            info('Removing %s' % self.name)
            if self.__bound:
                self.unbind()

            del self.__kbd_config
            del self.__kbd_function
        except AttributeError:
            pass

        super().__del__()
