#!/usr/bin/env python
import sys
from setuptools import setup
from pathlib import Path

with open('README.rst', 'r') as f:
    long_description = f.read()

meta = {}
with open(Path(__file__).parent / 'aioinflux' / '__init__.py') as f:
    exec('\n'.join(l for l in f if l.startswith('__')), meta)

test_requirements = [
    'pytest',
    'pytest-asyncio',
    'pytest-cov',
    'pyyaml',
    'pytz',
    'flake8',
    'pep8-naming',
    'flake8-docstrings',
    'flake8-rst-docstrings',
    'pygments',
]

if sys.version_info[:2] == (3, 6):
    test_requirements.append('dataclasses')

setup(name='aioinflux',
      version=meta['__version__'],
      description='Asynchronous Python client for InfluxDB',
      long_description=long_description,
      author='Gustavo Bezerra',
      author_email='gusutabopb@gmail.com',
      url='https://github.com/gusutabopb/aioinflux',
      packages=[
          'aioinflux',
          'aioinflux.serialization',
      ],
      include_package_data=True,
      python_requires='>=3.6',
      install_requires=['aiohttp>=3.0', 'ciso8601'],
      extras_require={
          'test': test_requirements,
          'docs': [
              'docutils',
              'sphinx',
              'sphinx_rtd_theme',
              'sphinx-autodoc-typehints',
          ],
          'pandas': [
              'pandas>=0.21',
              'numpy'
          ],
          'cache': [
              'aioredis>=1.2.0',
              'lz4>=2.1.0',
          ]
      },
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Database',
      ])
