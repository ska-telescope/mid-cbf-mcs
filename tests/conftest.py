# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""
A module defining a list of fixture functions that are shared across all the
ska-mid-cbf-tdc-mcs tests.
"""

from __future__ import absolute_import, annotations

import pytest

# Tango imports
import tango
from assertpy import add_extension

from ska_mid_cbf_tdc_mcs.testing.cbf_assertions import (
    cbf_has_change_event_occurred,
    cbf_hasnt_change_event_occurred,
)

# register the tracer custom assertions
add_extension(cbf_has_change_event_occurred)
add_extension(cbf_hasnt_change_event_occurred)


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Pytest hook; prints info about tango version.

    :param session: a pytest Session object
    """
    print(tango.utils.info())
