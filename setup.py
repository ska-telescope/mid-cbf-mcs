#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

setup(
    name='Mid CBF',
    version='0.0.0',
    description="",
    long_description=readme + '\n\n',
    author="James Jiang",
    author_email='james.jiang@nrc-cnrc.gc.ca',
    url='https://github.com/ska-telescope/mid-cbf-mcs',
    packages=[
        'CbfMaster',
	'CbfSubarray'
    ],
    package_dir={
	'CbfMaster': 'csplmc/CbfMaster',
	'CbfSubarray': 'csplmc/CbfSubarray'
    },
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
    install_requires=['pytango'],
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
