#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright© 2014 by Marc Culler and others.
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

import os
import socket, fcntl
import time
import struct
import threading
from igmpquerier.packets import IPv4Packet, IGMPv2Packet, IGMPv3MembershipQuery, IGMPv3Report


SIOCGIFADDR    = 0x8915
version        = '0.1'
__all__        = ['Querier']
query_group    = '224.0.0.1'
leave_group    = '224.0.0.2'
report_group   = '224.0.0.22' # used by v3 reports only


class Querier:
    """
    Sends an IGMP query packet at a specified time interval (in seconds).
    """
    def __init__(self, ifname, interval, msg_type, group, ttl):
        if os.getuid() != 0:
            raise RuntimeError('You must be root to create a Querier.')
        self.interval       = interval
        self.group          = group
        self.ttl            = ttl
        self.msg_type       = msg_type
        self.socket = sock = socket.socket(socket.AF_INET,
                                           socket.SOCK_RAW,
                                           socket.IPPROTO_RAW)
        time.sleep(1)  # Can't set options too soon (???)
        sock.settimeout(5)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        # Get the IP address of the chosen interface
        ifr = fcntl.ioctl(sock.fileno(), SIOCGIFADDR,
                    struct.pack('256s', ifname.encode()))
        self.source_address = source_address = socket.inet_ntoa(ifr[20:24])

        # Bind
        sock.bind((source_address, 0))

        # Build IGMP packet
        if (msg_type == "v1_query"):
            self.build_v1_query_packet()
        elif (msg_type == "v2_query"):
            self.build_v2_query_packet()
        elif (msg_type == "v3_query"):
            self.build_v3_query_packet()
        elif (msg_type == "v2_report"):
            self.build_v2_report()
        else:
            raise ValueError("IGMP message type not supported")

        self.listener = None
        self.elected = True
        self.stop = threading.Event()

    def build_v1_query_packet(self):
        igmp = IGMPv2Packet()
        igmp.type = 'query'
        # NOTE: max_response_time should be 0 for a v1 query
        #igmp.max_response_time = 100

        self.packet = ip = IPv4Packet()

        # Group-specific query
        if (self.group is not None):
            igmp.group = self.group
            self.dst   = self.group
            ip.dst     = self.group
        else:
            self.dst   = query_group
            ip.dst     = query_group

        ip.protocol = socket.IPPROTO_IGMP
        ip.ttl      = self.ttl
        ip.src      = self.source_address
        ip.data     = igmp

    def build_v2_query_packet(self):
        igmp = IGMPv2Packet()
        igmp.type = 'query'
        igmp.max_response_time = 100
        # NOTE: max response time will distinguish this query from v1 (it will
        # be interpreted as v2)

        self.packet = ip = IPv4Packet()

        # Group-specific query
        if (self.group is not None):
            igmp.group = self.group
            self.dst   = self.group
            ip.dst     = self.group
        else:
            self.dst   = query_group
            ip.dst     = query_group

        ip.protocol = socket.IPPROTO_IGMP
        ip.ttl      = self.ttl
        ip.src      = self.source_address
        ip.data     = igmp

    def build_v3_query_packet(self):
        igmp = IGMPv3MembershipQuery()
        igmp.type = 'query'
        igmp.max_response_time = 100

        self.packet = ip = IPv4Packet()

        # Group-specific query
        if (self.group is not None):
            igmp.group = self.group
            self.dst   = self.group
            ip.dst     = self.group
        else:
            self.dst = query_group
            ip.dst   = query_group


        ip.protocol = socket.IPPROTO_IGMP
        ip.ttl      = self.ttl
        ip.src      = self.source_address
        ip.data     = igmp

    def build_v2_report(self):
        assert(self.group is not None), "Group address undefined for v2_report"
        igmp = IGMPv2Packet()
        igmp.type = 'v2_report'
        igmp.group = self.group
        #igmp.max_response_time = 100

        self.packet = ip = IPv4Packet()
        self.dst    = report_group
        ip.protocol = socket.IPPROTO_IGMP
        ip.ttl      = self.ttl
        ip.src      = self.source_address
        ip.dst      = report_group
        ip.data     = igmp

    def run(self):
        print('Querier starting on {}'.format(self.source_address))
        wait = 0.0
        timeout = 0.1
        self.listener = QueryListener(self.source_address)

        while True:
            if self.stop.is_set():
                break

            time.sleep(timeout)
            wait += timeout
            if wait < self.interval:
                continue
            else:
                wait = 0.0

            elapsed = self.listener.elapsed()
            if self.elected:
                print('Send {} on {}'.format(self.msg_type, self.source_address))
                self.socket.sendto(self.packet.as_bytes(), (self.dst, 0))
                if elapsed < self.interval:
                    self.elected = False
                    print('Lost querier election, pausing on {}'.format(self.source_address))
            else:
                if (elapsed > 2 * self.interval):
                    print('Won querier election, resuming on {}'.format(self.source_address))
                    self.elected = True
            if not self.listener.thread.is_alive():
                print('Listener thread died, quitting on {}'.format(self.source_address))
                break

        self.listener.stop.set()
        self.socket.close()
        print('Querier quitting on {}'.format(self.source_address))


class QueryListener:
    """
    Manages the IGMP querier election process.  The elapsed() method returns
    the time since the last query packet from a higher priority device.
    """
    def __init__(self, address):
        self.address = self._ip_as_int(address)
        self._timestamp = 0  # the timestamp is shared data
        self.socket = sock = socket.socket(socket.AF_INET,
                                    socket.SOCK_RAW,
                                    socket.IPPROTO_IGMP)
        sock.bind(('224.0.0.1', 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.5)  # timeout for stopping thread
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = thread = threading.Thread(target=self.listen)
        #thread.daemon = True
        thread.start()

    def _ip_as_int(self, address):
        return struct.unpack("!I", socket.inet_aton(address))[0]

    def listen(self):
        while not self.stop.is_set():
            try:
                data, address = self.socket.recvfrom(65565)
            except socket.timeout:
                continue

            if data[20] == 17:  # make sure we got a query packet
                if self._ip_as_int(address[0]) < self.address:
                    self.lock.acquire()
                    self._timestamp = time.time()
                    self.lock.release()
        self.socket.close()

    def elapsed(self):
        """
        Return the time elapsed since receiving a query from a
        device with a lower ip address.
        """
        self.lock.acquire()
        result = time.time() - self._timestamp
        self.lock.release()
        return result
