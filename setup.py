#!/usr/bin/env python3

from setuptools import setup

setup(name='igmpquerier',
      version=0.3,
      description='IGMP querier service',
      author='Marc Culler, Balázs Póka',
      author_email='marc.culler@gmail.com, p.balazs@gmail.com',
      packages=['igmpquerier'],
      install_requires=['netifaces>0.7']
     )
