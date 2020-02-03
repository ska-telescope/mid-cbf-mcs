# -*- coding: utf-8 -*-
#
# This file is part of the CbfConfigurationPSS project
#
#
#
# Distributed under the terms of the none license.
# See LICENSE.txt for more info.

"""CbfConfigurationPSS

A generic base device for Observations for SKA.
"""

from . import release
from .SKAObsDevice import CbfConfigurationPSS, main

__version__ = release.version
__version_info__ = release.version_info
__author__ = release.author
