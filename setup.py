#!/usr/bin/env python
import sys
from setuptools import setup

if sys.version_info.major != 3 or sys.version_info.minor < 6:
    sys.exit('aioinflux supports Python>=3.6 only')

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(name='aioinflux',
      version='0.1.1',
      description='Asynchronous Python client for InfluxDB',
      long_description=long_description,
      author='Pluga AI',
      author_email='gusutabopb@gmail.com',
      url='https://github.com/plugaai/aioinflux',
      packages=['aioinflux'],
      install_requires=['aiohttp>=2.3.0',
                        'pandas>=0.21',
                        'numpy',
                        ],
      test_requires=['pytest', 'pytest-asyncio', 'pytest-cov'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
          'Topic :: Database',
      ])
