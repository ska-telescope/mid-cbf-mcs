#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from setuptools import setup


import os
import sys
import setuptools

setup_dir = os.path.dirname(os.path.abspath(__file__))
release_module = {}
release_filename = os.path.join(setup_dir, "src", "ska_mid_cbf_mcs", "release.py")
# pylint: disable=exec-used
exec(open(release_filename).read(), release_module)


with open('README.md') as readme_file:
    readme = readme_file.read()

pack = ['ska-mid-cbf-mcs']

setuptools.setup(
    name=release_module["name"],
    description=release_module["description"],
    version=release_module["version"],
    author=release_module["author"],
    author_email=release_module["author_email"],
    license=release_module["license"],
    url=release_module["url"],
    long_description=readme + '\n\n',
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    zip_safe=False,
    keywords='ska mid cbf mcs',
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
    entry_points={
        "console_scripts": [
            "CbfController=ska_mid_cbf_mcs.controller.controller_device:main",
            "CbfSubarray=ska_mid_cbf_mcs.subarray.subarray_device:main",
            "FspMulti=ska_mid_cbf_mcs.fsp.fsp_multi:main",
            "VccMulti=ska_mid_cbf_mcs.vcc.vcc_multi:main",
            "TalonLRU=ska_mid_cbf_mcs.talon_lru.talon_lru_device:main",
            "PowerSwitch=ska_mid_cbf_mcs.power_switch.power_switch_device:main",
            "TmCspSubarrayLeafNodeTest=ska_mid_cbf_mcs.tm_leaf_node:main",
        ]
    },
    test_suite='tests',
    install_requires=[
        'pytango >= 9.3.2',
        'ska-tango-base == 0.11.3'
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
