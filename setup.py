#!/usr/bin/env python3

from setuptools import setup

setup(
    name         = 'igmp-querier',
    version      = '0.3.1',
    description  = 'IGMP querier service',
    author       = 'Marc Culler, Balázs Póka, Takashi Nakamoto',
    author_email = 'marc.culler@gmail.com, p.balazs@gmail.com, takashi.nakamoto@nao.ac.jp',
    packages     = ['igmpquerier'],
    url          = 'https://github.com/tnakamot/querierd',
    license      = 'GPLv2',
    keywords     = ['IGMP', 'Querier', 'snooping', 'multicast'],
    classifiers  = ['Topic :: System :: Networking'],
)
