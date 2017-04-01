# hidrelayd

A daemon for controlling remotely controllable USB HID devices. This daemon
allows you to turn any Linux machine with a USB OTG port into a remotely
controllable USB keyboard/mouse device using the kernel's libcomposite module.

This is generally intended for use in controlling machines remotely in scenarios
that software based solutions such as OpenSSH can't cover. For instance,
controlling a machine that may not nessecarily even be booted into an operating
system. This is especially useful for controlling machines used for driver
development, where we may need to be able to control input in the BIOS or
bootloader. Of course there are more proper solutions for this, but they're much
more expensive then a $50 Beaglebone board. It can of course, be used for other
things as well if you put your imagination to it.

If you are simply trying to set your computer up so that you have basic remote
control over it, a solution such as OpenSSH is probably better for you.

## Requirements

- python 3
- [pyudev](https://pypi.python.org/pypi/pyudev)
- [kmod](https://pypi.python.org/pypi/kmod)
- A kernel with the following kernel options enabled as built-in or modules
  - `CONFIG_USB_LIBCOMPOSITE`
  - `CONFIG_USB_G_HID`
- A device with an OTG USB port such as a Beaglebone or a Raspberry Pi (must be
  a Model B or newer).

## Using

Right now hidrelayd is in very early development, and as such only has some of
the supporting code written. If you want to play around with it though, the
modules you want to play with are `hidrelayd.usb_gadget.UsbGadget` and
`hidrelayd.ghid.Keyboard`.
