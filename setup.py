#!/usr/bin/env python
from setuptools import setup

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(name='aioinflux',
      version='0.3.1',
      description='Asynchronous Python client for InfluxDB',
      long_description=long_description,
      author='Gustavo Bezerra',
      author_email='gusutabopb@gmail.com',
      url='https://github.com/plugaai/aioinflux',
      packages=['aioinflux'],
      include_package_data=True,
      python_requires='>=3.6',
      install_requires=['aiohttp>=3.0', 'ciso8601'],
      extras_require={'test': ['pytest',
                               'pytest-asyncio',
                               'pytest-cov',
                               'pyyaml',
                               'pytz',
                               ],
                      'pandas': ['pandas>=0.21', 'numpy']},
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
          'Topic :: Database',
      ])
