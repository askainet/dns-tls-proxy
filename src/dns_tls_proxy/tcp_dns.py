# -*- coding: utf-8 -*-

"""
tcp_dns module
"""

import logging
import struct


class TCPDNS:
    """
    Send and receive TCP DNS messages following RFC 1035
    https://tools.ietf.org/html/rfc1035#section-4.2.2
    """

    def __init__(self, sock):
        """
        Construct a new 'TCPDNS' object

        :param sock: The socket to use for IO
        :return: returns nothing
        """
        self.log = logging.getLogger(__name__)
        self.sock = sock

    def send(self, msg):
        """
        Send a TCP DNS message, prefixing the original DNS request with a two
        byte length field which gives the message length, excluding the prefix

        :param msg: The DNS message to send, without any extra field
        :return: returns nothing
        """
        msg_len = len(msg)
        full_msg = struct.pack("!H", msg_len) + msg
        self.log.debug('Sending TCP DNS message of size 2 + %s', msg_len)
        return self.sock.send(full_msg)

    def recv(self):
        """
        Receive a DNS request via a TCP DNS message
        The message is prefixed with a twp byte length field which gives the
        message length, excluding the prefix

        :return: The DNS request, excluding the length field prefix
        """
        self.log.debug('Reading TCP DNS length field...')
        len_field = self.sock.recv(2)
        msg_len, = struct.unpack('!H', len_field)
        self.log.debug('Received TCP DNS length field: %s', msg_len)

        self.log.debug('Reading DNS message...')
        msg = self.sock.recv(msg_len)
        self.log.debug('Received DNS message of length %s', len(msg))

        return msg
