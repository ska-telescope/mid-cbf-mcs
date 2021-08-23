#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from setuptools import setup


import os
import sys
import setuptools

setup_dir = os.path.dirname(os.path.abspath(__file__))
# make sure we use latest info from local code
sys.path.insert(0, setup_dir)

INFO = {}

with open('README.md') as readme_file:
    readme = readme_file.read()

pack = ['ska-mid-cbf-mcs']

setuptools.setup(
    name='ska-mid-cbf-mcs',
    version='0.5.4',
    description="SKA Mid.CBF MCS",
    long_description=readme + '\n\n',
    author="Taylor Huang",
    author_email='taylor.huang@mda.space',
    url='https://gitlab.com/ska-telescope/ska-mid-cbf-mcs',
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    license="BSD license",
    zip_safe=False,
    keywords='ska cbf',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    install_requires=[
        'pytango >= 9.3.2',
        'ska-tango-base >= 0.10.0'
    ],
    setup_requires=[
        # dependency for `python setup.py test`
        'pytest-runner',
        # dependencies for `python setup.py build_sphinx`
        'sphinx',
        'recommonmark'
    ],
    tests_require=[
        'pytest',
        'pytest-cov',
        'pytest-json-report',
        'pycodestyle',
    ],
    extras_require={
        'dev':  ['prospector[with_pyroma]', 'yapf', 'isort']
    }
)
