#!/usr/bin/python3
import os
import pyudev
import weakref

from enum import Enum
from struct import Struct

class HidProtocol(Enum):
    KEYBOARD = 1
    MOUSE = 2

class _Device():
    def _get_char_dev(self):
        if self.char_dev == None or self.char_dev.closed:
            self.char_dev = gadget.find_hidg_device(self.function)

    def __init__(self, gadget, protocol, report_length, report_descriptor):
        self.gadget = gadget
        self.function = gadget.create_function(protocol, report_length,
                                               report_descriptor)
        self.char_dev = None

    def sync(self):
        self.char_dev.flush()

class Keyboard(_Device):
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

    packet = Struct('cx6s')

    def __init__(self, gadget):
        super().__init__(gadget, HidProtocol.KEYBOARD.value, 8,
                         self.HID_DESCRIPTOR)

    @property
    def pressed_keys(self):
        return self.__pressed_keys

    def set_pressed(self, keys=set()):
        self._get_char_dev()

        modifier_mask = 0
        key_string = bytearray()

        for key in keys:
            try:
                modifier_mask |= Keyboard.Modifier(key).value
                continue
            except ValueError:
                pass

            assert len(key_string) < 6
            key_string.append(key)

        ret = self.char_dev.write(self.packet.pack(bytes([modifier_mask]),
                                                   bytes(key_string)))
        self.__pressed_keys = keys
