# -*- coding: utf-8 -*-

"""
main.py
"""

import sys
import logging
import configargparse
from . import __project_name__, __version__
from . import logger
from .portnumber import PortNumber
from .proxy import Proxy


def main():
    """
    Program main method
    """

    parser = configargparse.ArgumentParser(
        description='DNS-over-TLS proxy'
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        '--version',
        action='store_true',
        help='Show version'
    )

    group.add_argument(
        '-n', '--nameserver',
        dest='nameservers',
        metavar='<nameserver>:<port>:<CN-verify>',
        action='append',
        env_var='NAMESERVERS',
        help='Set the nameservers to forward DNS over TLS queries.'
             ' Use it multiple times to add more nameservers'
    )
    parser.add_argument(
        '-l', '--logfile',
        env_var='LOGFILE',
        help='Set a logfile instead of using STDERR'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        env_var='VERBOSE',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        env_var='DEBUG',
        help='Enable debug logging'
    )
    parser.add_argument(
        '-t', '--tcp',
        action='store_true',
        env_var='ENABLE_TCP',
        default=True,
        help='Enable TCP listener'
    )
    parser.add_argument(
        '-u', '--udp',
        action='store_true',
        env_var='ENABLE_UDP',
        default=True,
        help='Enable UDP listener'
    )
    parser.add_argument(
        '-s', '--stats',
        action='store_true',
        default=True,
        env_var='ENABLE_STATS',
        help='Enable stats logging'
    )
    parser.add_argument(
        '-p', '--port',
        default=15353,
        env_var='PORT',
        type=PortNumber,
        help='Port number to listen on for DNS queries'
    )
    parser.add_argument(
        '--pool-size',
        default=5,
        env_var='POOL_SIZE',
        type=int,
        help='Size of the nameservers connection pool'
    )

    args = parser.parse_args()

    if args.version:
        print('{} {}'.format(__project_name__, __version__))
        sys.exit(0)

    if not (args.udp or args.tcp):
        parser.error('At least one listener must be enabled using --tcp and/or --udp')

    if args.debug:
        loglevel = logging.DEBUG
    elif args.verbose:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING

    logger.setup(args.logfile, loglevel)

    nameservers = list()
    for arg_nameserver in args.nameservers:
        for nameserver in arg_nameserver.split(','):
            ip, port, cn = nameserver.split(':')
            nameservers.append((ip, int(port), cn))

    proxy = Proxy(
        nameservers=nameservers,
        port=args.port,
        tcp=args.tcp,
        udp=args.udp,
        stats=args.stats,
        pool_size=args.pool_size
    )
    proxy.start()
