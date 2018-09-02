import logging
from random import choice
from gevent import time
from gevent import lock
from gevent import queue
from gevent import socket
from gevent import ssl
from .socket_io import SocketIO


DEFAULT_CONNECTION_TIMEOUT = 1.0
DEFAULT_NETWORK_TIMEOUT = 1.0
BLACKLIST_TIME = 10


class TCPConnectionPool(object):

    def __init__(self, addresses, size=5):
        self.log = logging.getLogger(__name__)
        self._addresses = addresses
        self._semaphore = lock.BoundedSemaphore(size)
        self._socket_queue = queue.LifoQueue(size)
        self.connection_timeout = DEFAULT_CONNECTION_TIMEOUT
        self.network_timeout = DEFAULT_NETWORK_TIMEOUT
        self.size = size
        self._blacklist = list()
        self._bl_semaphore = lock.BoundedSemaphore(1)

    def _create_tcp_socket(self):
        """ tcp socket factory.
        """
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        return sock

    def _create_socket(self):
        """ might be overriden and super for wrapping into a ssl socket
            or set tcp/socket options
        """
        try:
            sock = self._create_tcp_socket()
        except Exception as exc:
            self.log.error('Error creating socket: %s', exc)
            raise

        try:
            address = self.get_address()
        except Exception:
            raise

        try:
            sock.settimeout(self.connection_timeout)
            self.log.debug('Connecting to host: %s', address[:2])
            sock.connect(address[:2])
            self.after_connect(sock, address)
            sock.settimeout(self.network_timeout)
            # Use the improved SocketIO methods
            sock = SocketIO(sock)
            return sock
        except Exception as exc:
            sock.close()
            self.log.warning('Error connecting to socket %s: %s', address, exc)
            self.add_blacklist(address)
            raise

    def get_socket(self):
        """ get a socket from the pool. This blocks until one is available.
        """
        self._semaphore.acquire()
        try:
            return self._socket_queue.get(block=False)
        except queue.Empty:
            try:
                return self._create_socket()
            except Exception:
                self._semaphore.release()
                raise

    def return_socket(self, sock):
        """ return a socket to the pool.
        """
        self.log.debug('Returning socket #%s to connection pool', sock.fileno())
        self._socket_queue.put(sock)
        self._semaphore.release()

    def release_socket(self, sock):
        """ call when the socket is no more usable.
        """
        self.log.debug('Deleting socket #%s', sock.fileno())
        try:
            sock.close()
        except Exception:
            pass
        self._semaphore.release()

    def after_connect(self, sock, address):
        pass

    def get_address(self):
        self.expire_blacklist()
        blacklist = [x['address'] for x in self._blacklist]
        available = [x for x in self._addresses if x not in blacklist]
        self.log.debug('Blacklisted addresses: %s', blacklist)
        self.log.debug('Available addresses: %s', available)
        if len(available):
            return choice(available)
        else:
            raise RuntimeError('All addresses are currently blacklisted')

    def add_blacklist(self, address):
        self.log.warning('Adding address %s to blacklist', address)
        item = {'address': address, 'timestamp': time.time()}
        self._blacklist.append(item)

    def expire_blacklist(self):
        self._bl_semaphore.acquire()
        new_blacklist = list()
        now = time.time()
        for item in self._blacklist:
            self.log.debug('Checking blacklist expiration for %s', item)
            if now - item['timestamp'] < BLACKLIST_TIME:
                new_blacklist.append(item)
            else:
                self.log.warning('Removing address %s from blacklist', item['address'])
        self._blacklist = new_blacklist
        self._bl_semaphore.release()


class TLSConnectionPool(TCPConnectionPool):
    """
    TLSConnectionPool creates connections wrapped with TLS

    :param addresses: list of tuples (address, port, hostname)
    :param port: port
    :param size: size of the connection pool
    """

    def __init__(self, addresses, size=5):
        super().__init__(addresses=addresses, size=size)
        self.log = logging.getLogger(__name__)
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.load_default_certs()

    def _create_tcp_socket(self):
        sock = super()._create_tcp_socket()
        return self.context.wrap_socket(sock)

    def after_connect(self, sock, address):
        super().after_connect(sock, address)
        ssl.match_hostname(sock.getpeercert(), address[2])
