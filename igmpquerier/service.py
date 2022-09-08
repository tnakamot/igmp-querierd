#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright© 2016 by Alexander Roessler.
# Based on the work of Mark Culler and others.
# This file is part of QuerierD.
#
# QuerierD is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# QuerierD is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with QuerierD.  If not, see <http://www.gnu.org/licenses/>.

from igmpquerier import Querier
import threading
import time
import sys
import argparse
import os


class QuerierInstance:
    def __init__(self, interface, interval, msg_type, group, ttl):
        self.interface = interface
        self.interval = interval
        self.querier = Querier(interface, interval, msg_type, group, ttl)
        self.thread = thread = threading.Thread(target=self.run)
        thread.daemon = True

    def run(self):
        self.querier.run()

    def stop(self):
        self.querier.stop.set()

    def start(self):
        self.thread.start()

    def join(self):
        self.thread.join()

def main():
    parser = argparse.ArgumentParser(description='This program periodically sends IGMP queries through the specified network interface.')

    parser.add_argument('-i', '--interface',
                        help='Network interface through which to send IGMP packets \
                        (required)', required=True)

    parser.add_argument('-t', '--type', choices=['v1_query', 'v2_query',
                                                 'v3_query', 'v2_report'],
                        default='v3_query',
                        help='Target IGMP message type to transmit \
                        (default: v3_query)')

    parser.add_argument('--interval', type=float,
                        help='IGMP transmission interval in seconds (default: 5 seconds)',
                        default=5.0)

    parser.add_argument('--ttl', type=int,
                        help='IP packet TTL (default: 1)', default=1)

    parser.add_argument('-g', '--group', default=None,
                        help='Target group for group-specific messages \
                        (default: None)')

    args = parser.parse_args()

    if os.getuid() != 0:
        print('You must be root to run a querier.')
        sys.exit(1)

    interval  = args.interval
    interface = args.interface
    msg_type  = args.type
    group     = args.group
    ttl       = args.ttl

    try:
        querier   = QuerierInstance(interface, interval, msg_type, group, ttl)
        querier.start()
        querier.join()
    except KeyboardInterrupt:
        pass

    sys.exit(0)

if __name__ == "__main__":
    main()
