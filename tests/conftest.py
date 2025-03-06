# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""
A module defining a list of fixture functions that are shared across all the
ska-mid-cbf-mcs tests.
"""

from __future__ import absolute_import, annotations

import pytest

# Tango imports
import tango


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Pytest hook; prints info about tango version.

    :param session: a pytest Session object
    """
    print(tango.utils.info())
