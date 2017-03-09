from enum import Enum

class KeyboardModifier(Enum):
    LEFT_CTRL   = 0x01
    RIGHT_CTRL  = 0x10
    LEFT_SHIFT  = 0x02
    RIGHT_SHIFT = 0x20
    LEFT_ALT    = 0x04
    RIGHT_ALT   = 0x40
    LEFT_META   = 0x08
    RIGHT_META  = 0x80
