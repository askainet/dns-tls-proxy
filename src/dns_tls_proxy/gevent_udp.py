# -*- coding: utf-8 -*-

"""
server_udp module
"""

import logging
from gevent.server import DatagramServer
from .request_handler import RequestHandlerUDP


class ServerUDP(DatagramServer):

    def __init__(self, listener, conn_pool, stats_queue=None):
        super().__init__(listener)
        self.log = logging.getLogger(__name__)
        self.conn_pool = conn_pool
        self.stats_queue = stats_queue

    def handle(self, data, address):
        self.log.info('New UDP request received from %s', address)

        request_handler = RequestHandlerUDP(
            address=address,
            socket=self.socket,
            conn_pool=self.conn_pool,
            data=data,
            stats_queue=self.stats_queue
        )
        result = request_handler.proxy_request()

        return result
