# -*- coding: utf-8 -*-

"""
request_handler module
"""

import logging
from gevent import time
import dns.message
import dns.rcode
from .tcp_dns import TCPDNS
from .socket_io import SocketIO


PROXY_REQUEST_TRIES = 3


class RequestHandler:

    def __init__(self, address, socket, conn_pool, stats_queue):
        self.log = logging.getLogger(__name__)
        self.address = address
        self.socket = socket
        self.conn_pool = conn_pool
        self.reply = None
        self.stats_queue = stats_queue
        self.dns_query = None

    def get_request(self):
        raise NotImplementedError

    def send_reply(self):
        raise NotImplementedError

    def stats(self):
        self.stats_queue.put({
            'listener': self.proto,
            'response_time': self.end_ts - self.start_ts
        })

    def parse_dns_message(self, msg):
        try:
            dns_msg = dns.message.from_wire(msg)
            self.log.debug('Parsed DNS message: %s', dns_msg)
            return dns_msg
        except Exception as exc:
            self.log.warning('Received bad DNS message: %s', exc)
            self.log.info('Original DNS message: %s', msg)
            return False

    def reply_servfail(self):
        reply = dns.message.Message(self.dns_query.id)
        reply.set_rcode(dns.rcode.SERVFAIL)
        self.log.warn('Reply to client with rcode SERVFAIL')
        return reply.to_wire()

    def proxy_request(self, **options):
        self.start_ts = time.time()

        request = self.get_request()
        self.dns_query = self.parse_dns_message(request)
        if not self.dns_query:
            return self.reply_servfail()

        success = False
        try_count = 0
        while not success and try_count < PROXY_REQUEST_TRIES:
            try_count += 1

            try:
                sock = self.conn_pool.get_socket()
            except OSError as exc:
                self.log.info('Unable to connect to nameserver, reconnecting...')
                continue
            except Exception as exc:
                self.log.error('Unexpected error connecting to nameserver: %s', exc)
                continue

            # Use TCP DNS application protocol
            tcp_dns = TCPDNS(sock)

            # Send DNS request to nameserver
            try:
                tcp_dns.send(request)
            except OSError as exc:
                self.log.info('Error sending request to nameserver (connection broken), reconnecting...')
                self.conn_pool.release_socket(sock)
                continue
            except Exception as exc:
                self.log.error('Unexpected error sending request to nameserver: %s', exc)
                self.conn_pool.release_socket(sock)
                continue

            # Get DNS reply from nameserver
            try:
                self.reply = tcp_dns.recv()
            except OSError as exc:
                self.log.info('Error reading reply from nameserver (connection broken), reconnecting...')
                self.conn_pool.release_socket(sock)
                continue
            except Exception as exc:
                self.log.error('Unexpected error receiving reply from nameserver: %s', exc)
                self.conn_pool.release_socket(sock)
                continue

            # We are done with the connecton, return it to the pool
            self.conn_pool.return_socket(sock)
            success = True

        if not success:
            self.log.error('Unable to forward request to any nameserver after %s tries', try_count)
            self.reply = self.reply_servfail()

        elif not self.parse_dns_message(self.reply):
            self.reply = self.reply_servfail()

        # Send DNS reply to client
        result = self.send_reply()

        self.end_ts = time.time()
        if self.stats_queue:
            self.stats()

        return result


class RequestHandlerTCP(RequestHandler):

    def __init__(self, address, socket, conn_pool, stats_queue):
        super().__init__(
            address=address,
            socket=socket,
            conn_pool=conn_pool,
            stats_queue=stats_queue
        )
        self.proto = 'TCP'

    def get_request(self):
        self.tcp_dns = TCPDNS(self.socket)
        try:
            request = self.tcp_dns.recv()
        except Exception as exc:
            self.log.error('Error receiving request from client #%s: %s',
                           self.socket.fileno(), exc)
            raise
        else:
            return request

    def send_reply(self):
        try:
            self.log.info('Sending reply to client %s', self.address)
            self.tcp_dns.send(self.reply)
        except Exception as exc:
            self.log.error('Error sending reply to client: %s', exc)
            raise


class RequestHandlerUDP(RequestHandler):

    def __init__(self, address, socket, conn_pool, stats_queue, data):
        super().__init__(
            address=address,
            socket=socket,
            conn_pool=conn_pool,
            stats_queue=stats_queue
        )
        self.proto = 'UDP'
        self.data = data

    def get_request(self):
        return self.data

    def send_reply(self):
        try:
            self.log.info('Sending reply to client %s', self.address)
            socketio = SocketIO(self.socket)
            socketio.sendto(self.reply, self.address)
        except Exception as exc:
            self.log.error('Error sending reply to client: %s', exc)
            raise
