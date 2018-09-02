# -*- coding: utf-8 -*-

"""
proxy module
"""

import sys
import logging
import gevent
from gevent import signal

from .gevent_tcp import ServerTCP
from .gevent_udp import ServerUDP
from .connection_pool import TLSConnectionPool
from .stats import Stats


class Proxy:
    """
    Create a 'Proxy' service to forward DNS queries to the configured
    nameservers using DNS-over-TLS
    """

    def __init__(self, nameservers, port=53, tcp=True, udp=False, stats=False,
                 pool_size=5):
        """
        Construct a new 'Proxy' object

        :param nameservers: List of nameserver to forward DNS-over-TLS queries
        :param port: Listen on this port
        :return: returns nothing
        """
        self.log = logging.getLogger(__name__)

        self.nameservers = nameservers
        self.log.info('Using nameservers: %s', self.nameservers)
        self.port = port
        self.log.info('Using port: %s', self.port)
        self.tcp = tcp
        self.udp = udp
        self.servers = []
        self.pool_size = pool_size
        self.stats = Stats() if stats else False

    def _sig_term(self, signum, frame):
        self.log.warning('Received SIGTERM signal')
        raise SystemExit('Received SIGTERM signal')

    def start(self):
        """
        Start the proxy service
        :return: returns nothing
        """
        self.log.info('Starting DNS TLS proxy service...')

        self.conn_pool = TLSConnectionPool(
            addresses=self.nameservers,
            size=self.pool_size
        )

        signal.signal(signal.SIGTERM, self._sig_term)

        try:

            try:
                if self.tcp:
                    self.log.info('Starting TCP listener on port %i...', self.port)
                    server = ServerTCP(
                        listener=':{}'.format(self.port),
                        conn_pool=self.conn_pool,
                        stats_queue=self.stats.queue() if self.stats else None
                    )
                    self.servers.append(server)
                    server.start()
                if self.udp:
                    self.log.info('Starting UDP listener on port %i...', self.port)
                    server = ServerUDP(
                        listener=':{}'.format(self.port),
                        conn_pool=self.conn_pool,
                        stats_queue=self.stats.queue() if self.stats else None
                    )
                    self.servers.append(server)
                    server.start()

            except Exception as exc:
                self.log.critical('starting server failed: %s', exc)
                sys.exit(1)

            if self.stats:
                self.log.info('Starting stats collector...')
                gevent.spawn(self.stats.collector())

            gevent.wait()

        except (SystemExit, KeyboardInterrupt):
            self.log.warning('Stoping proxy service...')

        except Exception as exc:
            self.log.critical('Unexpected error: %s', exc)
            sys.exit(1)

        finally:
            for server in self.servers:
                self.log.info('Stoping listener %s...', server)
                server.stop()
