#!/usr/bin/python3

from setuptools import setup, find_packages
from hidrelayd.__version__ import __version__
setup(
    name="hidrelayd",
    version=__version__,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'hidrelayd = hidrelayd.__main__'
        ]
    },

    install_requires=[
        'kmod',
        'pyudev'
    ],

    author="Lyude Paul",
    author_email="thatslyude@gmail.com",
    description="Daemon for remotely-controllable HID devices"
)
