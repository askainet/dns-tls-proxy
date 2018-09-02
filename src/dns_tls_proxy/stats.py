# -*- coding: utf-8 -*-

"""
stats module
"""

import logging
from collections import defaultdict

from gevent import time
from gevent.queue import Queue


STATS_INTERVAL = 10


class Stats:
    """
    Create a 'Stats' collector and reporter
    """

    def __init__(self, interval=STATS_INTERVAL):
        """
        Construct a new 'Stats' object

        :param listeners: List of enabled listeners to collect stats from
        :return: returns nothing
        """
        self.log = logging.getLogger(__name__)
        self.log.debug('Init stats collector...')
        self.stats_queue = Queue()
        self.stats_store = defaultdict(lambda: defaultdict(lambda: 0))
        now = time.time()
        self.start_ts = now
        self.stats_ts = now

    def queue(self):
        return self.stats_queue

    def show(self):
        now = time.time()
        interval_elapsed = now - self.stats_ts
        self.stats_ts = now

        self.log.warning(
            '--- Stats of the proxy: #requests %i / qps %.02f / avg_time %.02fms',
            self.stats_store['TCP']['count'] + self.stats_store['UDP']['count'],
            (self.stats_store['TCP']['interval_count'] + self.stats_store['UDP']['interval_count']) / interval_elapsed,
            (self.stats_store['TCP']['interval_response_time'] + self.stats_store['UDP']['interval_response_time']) / 2 / interval_elapsed
        )

        for listener in self.stats_store.keys():
            self.log.warning(
                '--- Stats of %s listener: #requests %i / qps %.02f / avg_time %.02fms',
                listener,
                self.stats_store[listener]['count'],
                self.stats_store[listener]['interval_count'] / interval_elapsed,
                self.stats_store[listener]['interval_response_time'] / interval_elapsed
            )
            self.stats_store[listener]['interval_count'] = 0
            self.stats_store[listener]['interval_response_time'] = 0

    def collector(self):
        for msg in self.stats_queue:
            listener = msg['listener']
            self.stats_store[listener]['count'] += 1
            self.stats_store[listener]['interval_count'] += 1
            self.stats_store[listener]['interval_response_time'] += msg['response_time']

            if time.time() - self.stats_ts > STATS_INTERVAL:
                self.show()
