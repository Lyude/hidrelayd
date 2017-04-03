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

__all__ = ["Keyboard"]

class HidProtocol(Enum):
    KEYBOARD = 1
    MOUSE = 2

class Device():
    def __init__(self, gadget, protocol):
        self.gadget = gadget
        self.function = gadget.create_function(protocol, self.packet.length,
                                               self.HID_DESCRIPTOR)
        self.char_dev = None

    def _io_func(func):
        def func_wrapper(self, *args, **kwargs):
            if self.char_dev == None or self.char_dev.closed:
                self.char_dev = self.gadget.find_hidg_device(self.function)

            return func(self, *args, **kwargs)
        return func_wrapper

class Keyboard(Device):
    HID_DESCRIPTOR = bytes([
        0x05, 0x01, 0x09, 0x06, 0xa1, 0x01, 0x05, 0x07, 0x19, 0xe0, 0x29, 0xe7,
        0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01,
        0x75, 0x08, 0x81, 0x03, 0x95, 0x05, 0x75, 0x01, 0x05, 0x08, 0x19, 0x01,
        0x29, 0x05, 0x91, 0x02, 0x95, 0x01, 0x75, 0x03, 0x91, 0x03, 0x95, 0x06,
        0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65,
        0x81, 0x00, 0xc0
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
