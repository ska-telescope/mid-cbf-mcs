# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Partially ported from the SKA Low MCCS project:
# https://gitlab.com/ska-telescope/ska-low-mccs/-/blob/main/testing/src/tests/conftest.py
#
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
from assertpy import add_extension

from ska_mid_cbf_mcs.testing.cbf_assertions import (
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


@pytest.fixture(name="delay_model_test", scope="session")
def init_delay_model_test_fixture():
    """
    Return a delay model test object.

    :return: a DelayModelTest object, with a method for creating
    the delay model input used for tests
    """

    class DelayModelTest:
        def __init__(self: DelayModelTest) -> None:
            """
            No initialization required.
            """

        def create_test_dm_obj_all(
            self: DelayModelTest,
            delay_model_all_obj: dict,
            receptors_under_test: list[int],
        ) -> dict:
            dm_num_entries = len(delay_model_all_obj)
            # TODO: receptor values are hardcoded
            receptors_to_remove = list(
                set(["SKA001", "SKA100", "SKA036", "SKA063"])
                - set(receptors_under_test)
            )

            if receptors_to_remove:
                for i_dm in range(dm_num_entries):
                    # Remove the entries from the delay models that are NOT
                    # among receptors_under_test:
                    for i_rec in receptors_to_remove:
                        for jj, entry in enumerate(
                            delay_model_all_obj[i_dm]["receptor_delays"]
                        ):
                            if entry["receptor"] == i_rec:
                                delay_model_all_obj[i_dm][
                                    "receptor_delays"
                                ].pop(jj)

            return delay_model_all_obj

    return DelayModelTest()
