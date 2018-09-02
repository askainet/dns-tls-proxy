# -*- coding: utf-8 -*-

"""
Socket_io module
"""

import logging
from gevent import time
from gevent import ssl
from gevent.select import select


RECV_BUFFER_LEN = 16384
RECV_READ_TIMEOUT = 500 / 1000
RECV_TOTAL_TIMEOUT = 5000
SEND_WRITE_TIMEOUT = 500 / 1000
SEND_TOTAL_TIMEOUT = 5000


class SocketIO:
    """
    Use sockets with better send and receive methods
    Supports non-blocking socket reads also for SSL socks
    """

    def __init__(self, sock):
        """
        Construct a new 'SocketIO' object

        :param sock: The socket to use for IO
        :return: returns nothing
        """
        self.log = logging.getLogger(__name__)
        self.sock = sock

    def fileno(self):
        return self.sock.fileno()

    def send(self, data):
        """
        Write data top the socket
        Track how much data has been sent and timeout if not able to finish
        """
        length = len(data)
        total_sent = 0
        start_time = time.time()
        while total_sent < length:

            if time.time() - start_time > SEND_TOTAL_TIMEOUT:
                self.log.info('sock #%s write timeout', self.sock.fileno())
                raise OSError('sock #%s write timeout', self.sock.fileno())

            total_sent += self.sock.send(data)

    def sendall(self, data):
        """ No customization here, it just uses the original sendall() method """
        return self.sock.sendall(data)

    def sendto(self, data, address):
        """ No customization here, it just uses the original sendto() method """
        return self.sock.sendto(data, address)

    def recv(self, length=RECV_BUFFER_LEN):
        """
        Read data from the socket using non-blocking select() with timeout

        If using SSLsocket, try to read right away in case there is data
        available in the SSL buffer, use select() if not.
        This is needed because select() checks the underlying socket and it's
        probable that it has no more data to be read because it was already
        passed to the SSL buffer in the SSL wraper socket
        """
        chunks = []
        total_recv = 0

        start_time = time.time()

        while total_recv < length:

            if time.time() - start_time > RECV_TOTAL_TIMEOUT:
                self.log.info('sock #%s read timeout', self.sock.fileno())
                raise OSError('sock #%s read timeout', self.sock.fileno())

            if self.sock.__class__.__name__ == 'SSLSocket':
                try:
                    chunk = self.sock.recv(
                        min(length - total_recv, RECV_BUFFER_LEN))
                except ssl.SSLWantReadError as exc:
                    self.log.debug('sock #%s SSL needs more data from TCP sock: %s', exc)
                    pass
                else:
                    self.log.debug('sock #%s received %s bytes of SSL data',
                                   self.sock.fileno(), len(chunk))

                    if chunk == b'':
                        self.log.info('sock #%s connection broken',
                                      self.sock.fileno())
                        raise OSError('sock #%s connection broken',
                                      self.sock.fileno())

                    chunks.append(chunk)
                    total_recv += len(chunk)
                    continue

            (read, write, error) = select(
                [self.sock], [], [self.sock], RECV_READ_TIMEOUT)

            if self.sock in read:
                self.log.debug('sock #%s is ready to read: %s',
                               self.sock.fileno(), read)
                chunk = self.sock.recv(
                    min(length - total_recv, RECV_BUFFER_LEN))

                self.log.debug('sock #%s received %s bytes of data',
                               self.sock.fileno(), len(chunk))

                if chunk == b'':
                    self.log.info('sock #%s connection broken',
                                  self.sock.fileno())
                    raise OSError('sock #%s connection broken',
                                  self.sock.fileno())

                chunks.append(chunk)
                total_recv += len(chunk)

            else:
                self.log.warning('sock #%s not ready to read',
                                 self.sock.fileno())

        return b''.join(chunks)
