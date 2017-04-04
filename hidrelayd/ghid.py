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
import pyudev
import weakref

from enum import Enum
from struct import Struct

__all__ = ["Keyboard", "Mouse"]

class HidProtocol(Enum):
    KEYBOARD = 1
    MOUSE = 2

class Device():
    def __init__(self, gadget, protocol):
        self.gadget = gadget
        self.function = gadget.create_function(protocol, self.packet.size,
                                               self.HID_DESCRIPTOR)
        self.char_dev = None

    class GadgetUnboundError(Exception):
        def __init__(self):
            super().__init__("The UsbGadget for this device is not bound to anything")

    def _io_func(func):
        def func_wrapper(self, *args, **kwargs):
            if self.char_dev == None or self.char_dev.closed:
                try:
                    self.char_dev = self.gadget.find_hidg_device(
                        self.function)
                except pyudev.DeviceNotFoundByNumberError:
                    raise Device.GadgetUnboundError()

            return func(self, *args, **kwargs)
        return func_wrapper

class Keyboard(Device):
    HID_DESCRIPTOR = bytes([
        0x05, 0x01, # USAGE_PAGE (Generic Desktop)
        0x09, 0x06, # USAGE (Keyboard)
        0xa1, 0x01, # COLLECTION (Application)
        0x05, 0x07, #   USAGE_PAGE (Keyboard)
        0x19, 0xe0, #   USAGE_MINIMUM (KB Leftcontrol)
        0x29, 0xe7, #   USAGE_MAXIMUM (KB Right GUI)
        0x15, 0x00, #   LOGICAL_MINIMUM (0)
        0x25, 0x01, #   LOGICAL_MAXIMUM (1)
        0x75, 0x01, #   REPORT_SIZE (1)
        0x95, 0x08, #   REPORT_COUNT (8)
        0x81, 0x02, #   INPUT (Var)
        0x95, 0x01, #   REPORT_COUNT (1)
        0x75, 0x08, #   REPORT_SIZE (8)
        0x81, 0x03, #   INPUT (Cnst, Var)
        0x95, 0x05, #   REPORT_COUNT (5)
        0x75, 0x01, #   REPORT_SIZE (1)
        0x05, 0x08, #   USAGE_PAGE (LED)
        0x19, 0x01, #   USAGE_MINIMUM (1)
        0x29, 0x05, #   USAGE_MAXIMUM (5)
        0x91, 0x02, #   OUTPUT (Var)
        0x95, 0x01, #   REPORT_COUNT (1)
        0x75, 0x03, #   REPORT_SIZE (3)
        0x91, 0x03, #   OUTPUT(Cnst, Var)
        0x95, 0x06, #   REPORT_COUNT (6)
        0x75, 0x08, #   REPORT_SIZE (8)
        0x15, 0x00, #   LOGICAL_MINIMUM (0)
        0x25, 0x65, #   LOGICAL_MAXIMUM (101)
        0x05, 0x07, #   USAGE_PAGE (Keyboard)
        0x19, 0x00, #   USAGE_MINIMUM (None)
        0x29, 0x65, #   USAGE_MAXIMUM (KB Application)
        0x81, 0x00, #   INPUT ()
        0xc0        # END_COLLECTION
    ])

    class Modifier(Enum):
        LEFT_CTRL   = 0x01
        LEFT_SHIFT  = 0x02
        LEFT_ALT    = 0x04
        LEFT_META   = 0x08
        RIGHT_CTRL  = 0x10
        RIGHT_SHIFT = 0x20
        RIGHT_ALT   = 0x40
        RIGHT_META  = 0x80

    MODIFIER_MASK = 0xFF
    packet = Struct('cx6s')

    def __init__(self, gadget):
        super().__init__(gadget, HidProtocol.KEYBOARD.value)
        self.__pressed_keys = []
        self.__modifier_mask = 0

    @property
    def pressed_keys(self):
        return self.__pressed_keys

    @property
    def modifier_mask(self):
        return self.__modifier_mask

    @Device._io_func
    def set_pressed(self, modifier_mask=0, keys=[]):
        assert not modifier_mask & ~self.MODIFIER_MASK
        assert len(keys) <= 6

        self.char_dev.write(self.packet.pack(bytes([modifier_mask]),
                                             bytes(keys)))
        self.__pressed_keys = keys
        self.__modifier_mask = modifier_mask

class Mouse(Device):
    HID_DESCRIPTOR = bytes([
        0x05, 0x01, # USAGE_PAGE (Generic Desktop)
        0x09, 0x02, # USAGE (Mouse)
        0xa1, 0x01, # COLLECTION (Application)
        0x09, 0x01, #   USAGE (Pointer)
        0xa1, 0x00, #   COLLECTION (Physical)
        0x05, 0x09, #     USAGE_PAGE (Button)
        0x19, 0x01, #     USAGE_MINIMUM (Button 1)
        0x29, 0x03, #     USAGE_MAXIMUM (Button 3)
        0x15, 0x00, #     LOGICAL_MINIMUM (0)
        0x25, 0x01, #     LOGICAL_MAXIMUM (1)
        0x95, 0x03, #     REPORT_COUNT (3)
        0x75, 0x01, #     REPORT_SIZE (1)
        0x81, 0x02, #     INPUT (Data,Var,Abs)
        0x95, 0x01, #     REPORT_COUNT (1)
        0x75, 0x05, #     REPORT_SIZE (5)
        0x81, 0x03, #     INPUT (Cnst,Var,Abs)
        0x05, 0x01, #     USAGE_PAGE (Generic Desktop)
        0x09, 0x30, #     USAGE (X)
        0x09, 0x31, #     USAGE (Y)
        0x15, 0x81, #     LOGICAL_MINIMUM (-127)
        0x25, 0x7f, #     LOGICAL_MAXIMUM (127)
        0x75, 0x08, #     REPORT_SIZE (8)
        0x95, 0x02, #     REPORT_COUNT (2)
        0x81, 0x06, #     INPUT (Data,Var,Rel)
        0xc0,       #   END_COLLECTION
        0xc0        # END_COLLECTION
    ])

    """
    Layout:
      Button bitmask (1 byte)
      X-translation (1 byte)
      Y-translation (1 byte)
    """
    packet = Struct('ccc')

    def Button(Enum):
        LEFT   = (1 << 0)
        RIGHT  = (1 << 1)
        MIDDLE = (1 << 2)

    BUTTON_MASK = 0x7

    def __init__(self, gadget):
        super().__init__(gadget, HidProtocol.MOUSE.value)
        self.__btn_mask = 0

    @property
    def btn_mask(self):
        return self.__btn_mask

    @Device._io_func
    def set_pressed(self, btn_mask=0):
        assert not btn_mask & ~self.BUTTON_MASK

        self.char_dev.write(self.packet.pack(bytes([btn_mask]),
                                             bytes([0]), bytes([0])))
        self.__btn_mask = btn_mask

    @Device._io_func
    def move(self, x, y):
        self.char_dev.write(self.packet.pack(bytes([self.__btn_mask]),
                                             bytes([x]), bytes([y])))
