"""
A module defining a list of fixture functions that are shared across all the skabase
tests.
"""

from __future__ import absolute_import
#import mock
import pytest
import importlib
import sys
sys.path.insert(0, "../commons")

from tango import DeviceProxy
from tango.test_context import DeviceTestContext
import global_enum

@pytest.fixture(scope="class")
def create_vcc_proxy():
    return DeviceProxy("mid_csp_cbf/vcc/001")

@pytest.fixture(scope="class")
def create_band_12_proxy():
    return DeviceProxy("mid_csp_cbf/vcc_band12/001")

@pytest.fixture(scope="class")
def create_band_3_proxy():
    return DeviceProxy("mid_csp_cbf/vcc_band3/001")

@pytest.fixture(scope="class")
def create_band_4_proxy():
    return DeviceProxy("mid_csp_cbf/vcc_band4/001")

@pytest.fixture(scope="class")
def create_band_5_proxy():
    return DeviceProxy("mid_csp_cbf/vcc_band5/001")
