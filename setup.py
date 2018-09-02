# -*- coding: utf-8 -*-

"""
setup.py
"""

from setuptools import setup
from setuptools import find_packages

with open('README.md', 'r') as fh:
    LONG_DESCRIPTION = fh.read()

setup(
    name='dns-tls-proxy',
    version='0.0.1',
    author='Ivan Lopez',
    author_email='ivan@askai.net',
    description='DNS to DNS-over-TLS proxy',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'dnspython',
        'gevent',
        'ConfigArgParse'
    ],
    python_requires='>=3.4, <4',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: POSIX'
    ],
    entry_points={
        'console_scripts': [
            'dns-tls-proxy = dns_tls_proxy.main:main',
        ],
    },
    test_suite='tests'
)
