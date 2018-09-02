# -*- coding: utf-8 -*-

"""
server_tcp module
"""

import logging
from gevent.server import StreamServer
from .request_handler import RequestHandlerTCP


class ServerTCP(StreamServer):

    def __init__(self, listener, conn_pool, stats_queue=None):
        super().__init__(listener)
        self.log = logging.getLogger(__name__)
        self.conn_pool = conn_pool
        self.stats_queue = stats_queue

    def handle(self, source, address):
        self.log.info('New TCP request received from %s', address)

        request_handler = RequestHandlerTCP(
            address=address,
            socket=source,
            conn_pool=self.conn_pool,
            stats_queue=self.stats_queue
        )
        result = request_handler.proxy_request()

        return result
