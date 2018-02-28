#!/usr/bin/env python
import sys
from setuptools import setup

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(name='aioinflux',
      version='0.1.2',
      description='Asynchronous Python client for InfluxDB',
      long_description=long_description,
      author='Pluga AI',
      author_email='gusutabopb@gmail.com',
      url='https://github.com/plugaai/aioinflux',
      packages=['aioinflux'],
      python_requires='>=3.6',
      install_requires=['aiohttp>=3.0',
                        'pandas>=0.21',
                        'numpy',
                        ],
      extras_require={'test': ['pytest', 'pytest-asyncio', 'pytest-cov']},
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
          'Topic :: Database',
      ])
