# igmp-querierd

igmp-querierd is a Python implementation of [IGMP Querier](https://en.wikipedia.org/wiki/IGMP_snooping#IGMP_querier). If your network has a L2 switch that is capable of [IGMP snooping](https://en.wikipedia.org/wiki/IGMP_snooping), but if the network does not include any L3 router or network device that can acts as an IGMP Querier, the IGMP snooping function may not work as expected. In the worst case, some multicast packets may not be delivered properly. In order to establish multicast communication properly, you may add a L2 switch or a L3 router with IGMP Querier capability to your network or run this igmp-querier on one of Linux or Unix-like machines in the same network. In principle, igmp-querier keeps sending IGMP queries to the specified network.

You may want to read ["Why avahi and bonjour don't work on your home network and how to fix them"](#why-avahi-and-bonjour-dont-work-on-your-home-network-and-how-to-fix-them) to understand the background and how multicasting works, but please note that its usage is not limited to avahi or bonjour. igmp-querierd is useful for any other protocols that rely on multicasting.

## Installation

There are two steps to install igmp-querierd.

### Step 1: Installing python package

First you need to install a python package named `igmpquerier`.
If you have `pip` for Python3 installed, then the command

    sudo pip install .

should install the `igmpquerier` python package.

### Step 2: Set up as a system service

_Note: instructions below assume that your have a modern Linux distribution with systemd._

Step 2 is to set up igmp-querierd as a system service.  This involves copying a couple of files into your system directories, and must be done as root.  The details depend on your operating system. Here are the details:

Copy the service file to the systemd directory:

    sudo cp lib/systemd/system/querierd.service /etc/systemd/system

 * Don't forget to check the permissions!
 * To change the IGMP broadcast interval add `-i <interval>` to the `querierd.service` file.
 * You may find more options by running `python -m igmpquerier.service -h`.

The systemd service is now ready to be configured:

    sudo systemctl daemon-reload
    sudo systemctl start querierd.service

Wait a few seconds and check the status of the service:

    sudo systemctl status querierd.service

After you have approved that everything works fine its time to enable the service to be started at boot:

    sudo systemctl enable querierd.service

## Uninstall

For clean uninstallation, first make sure that the systemd service is stopped and disabled:

    sudo systemctl stop querierd.service
    sudo systemctl disable querierd.service

And then, remove /etc/systemd/system/querierd.service. After that, run command below to uninstall the python package from your system:

    sudo pip uninstall igmp-querier

## Testing

If you want to test igmp-querierd before installing it to your system, run

    $ sudo python -m igmpquerier.service -i eth0

in the root directory of this git repository. Then, run the command below to watch the IGMP traffic:

    $ sudo tcpdump -nv -ieth0 igmp

(replace eth0 by the appropriate interface on your computer).

Also, you can run avahi-browse to check that all of your devices and
services are visible:

    $ avahi-browse -at

## Why avahi and bonjour don't work on your home network and how to fix them

An internet search turns up lots and lots of reports of problems with
avahi and bonjour of the following general nature: "when I first start
up my XXX device / service it works fine; all the devices can see it.
But after a certain time, XXX disappears.  Other devices cannot see
it."  A typical example is
[Bug #657553](http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=657553)
which remains unresolved as of January 2014.



When the avahi developers respond to these complaints, they usually
say it is not their fault and refer the plaintiff to
[FAQ #15](http://avahi.org/wiki/Avah4users#FAQ) which says

  "you most likely are experiencing trouble with a broken network
  driver or WLAN AP, which doesn't properly support IP multicasting."

Well, great.  But what can be done about it?

### What is going on?

To explain the problem we need a little background on IP multicasting
and IGMP snooping.

Multicasting was designed for delivering high-bandwidth data streams,
TV in other words, across a network without overloading the network.
If an internet TV station had to send its video stream to each
subscriber individually, the outgoing network link from the station
would have to carry many, many identical data streams.  There is no
way that they could possibly get enough bandwidth.  And anyway it is
silly to send many copies of the same stream.

Multicasting avoids this problem by providing a way for a single
stream to be delivered to many subscribers.  The outgoing stream is
directed to a single multicast address belonging to a "multicast
group".  When a router receives the packets of such a stream on an
upstream port, it sends a copy to each of its downstream ports
*provided that some downstream node on that port has joined the
multicast group.* How does it know whether any downstream nodes
belong to the group? That job is handled by the IGMP protocol.

But the bandwidth problem is not limited to routers.  It also occurs
with swithes on a local area network, especially when wireless is
involved.  If one person on your LAN is watching TV on their iPad,
connected to a wireless access point which is connected to one port of
your DNS or cable router, then your router needs to deliver the stream
to the WAP.  But the WAP is most likely behaving as a switch, not a
router.  So it is not supposed to be interpreting packets, just
forwarding them to the devices connected to it.  If this rule were
followed strictly, it would mean that any device connected to that WAP
would receive the video stream, even if it is not watching TV. And
that video stream uses a substantial portion of the bandwidth
available on the wireless link.  So innocent devices who are not
watching TV would experience a significant slowdown.  To deal with
this problem, switches use IGMP snooping.  See the
[wikipedia article](http://en.wikipedia.org/wiki/IGMP_snooping#IGMP_querier).

The idea of IGMP snooping is that a switch will watch the IGMP traffic
generated by the devices it serves in order to decide which multicast
groups each device wants to belong to.  The switch then notifies its
upstream router that it wants to subscribe to all groups which have at
least one member among the nodes served by the switch.  If no device
on a switch port wants to belong to a certain group, then the switch
will not forward any multicast packets for that group.  A key point is
this: while IGMP v2 provides a way for a device to leave a group, the
switch cannot count on a device sending a leave request.  First of
all, the leave requests did not exist in IGMP v1, which the device may
be using.  Secondly, the device might crash.  Therefore, a switch
which does IGMP snooping will set an "IGMP membership timeout."  When
a device subscribes to a multicast group it must renew its membership
before the timeout expires; otherwise the switch will mark it as not
belonging to the group and stop sending it packets for that group.

But, you ask, what does this have to do with avahi or bonjour?  Well,
it turns out that those protocols also use multicasting.  There is a
multicast group for mDNS (the address is 224.0.0.251).  All of the
communication related to avahi or bonjour uses multicast packets sent
to this multicast group.

So now we see the problem.  The avahi or bonjour daemon on your device
joins the mDNS multicast group when it starts up.  But it is not the
job of the avahi-daemon to ensure that your device remains a member of
the mDNS group.  That job is supposed to be handled automatically by
the switches and routers on your network, using IGMP.  The reason your
device disappears after a while is that a switch, probably your WAP,
does not hear any subsequent IGMP join requests from your device.  So,
after a while, the switch stops forwarding any mDNS packets, and the
device "disappears".

### What can be done?

To understand how to deal with this we need to discuss one more
feature of the IGMP protocol and IGMP snooping.  In order for your
device to remain a member of the mDNS group, it needs to periodically
send a request (actually called a *report* in IGMP) to join the mDNS
group before the switch decides to remove it from the group.  As
explained in the Wikipedia page, the IGMP protocol deals with this by
requiring that each network have a router which functions as an "IGMP
querier".  In order to avoid unnecessary network traffic, IGMP v2
specifies that this router should be "elected" by choosing the router
with the lowest IP address.  The job of the querier is simply to send
an IGMP *query packet* to the multicast broadcast address (224.0.0.1)
every so often.  Switches are required to forward the query packets to
all of their ports.  When a device receives a query packet it responds
(after a random delay and subject to a countdown timer) by sending
reports requesting to join all groups that it wants to belong to.

Unfortunately, however, many cheap home network routers like the ones
that you and I buy do not provide an IGMP querier.  That is the reason
that avahi and bonjour do not work on your home network.

The good news is that this problem is easy to fix.  All we need to do
is run a little daemon on one device which sends an IGMP query to the
multicast broadcast address at regular intervals.  igmp-querierd provides
such a daemon.  Once you start it up on one or more of your computers
your devices will stop disappearing.

The igmp-querierd daemon will participate in the querier election process,
so you can run igmp-querierd daemons on several devices on your network,
some of which may not be running all the time.  The igmp-querierd daemons
will cooperate with any routers or other igmp-querierd daemons, so only
one of them will provide the querier service at a time.

