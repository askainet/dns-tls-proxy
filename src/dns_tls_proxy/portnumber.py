# -*- coding: utf-8 -*-

"""
portnumber.py
"""

from argparse import ArgumentTypeError

___MIN_PORT_NUMBER__ = 1
___MAX_PORT_NUMBER__ = 2**16 - 1


class PortNumber(int):
    """
    Validate a port number
    """

    # pylint: disable-msg=too-few-public-methods
    def __init__(self, value):
        self._value = int(value)
        if not ___MIN_PORT_NUMBER__ <= self._value <= ___MAX_PORT_NUMBER__:
            raise ArgumentTypeError(
                'port numbers must be integers between 1 and %i'
                % ___MAX_PORT_NUMBER__)
        int.__init__(value)

    def __int__(self):
        return self._value
