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

from typing import Dict, List, Set, cast

import pytest

# Tango imports
import tango
import yaml


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Pytest hook; prints info about tango version.

    :param session: a pytest Session object
    """
    print(tango.utils.info())


with open("tests/testbeds.yaml", "r") as stream:
    _testbeds: Dict[str, Set[str]] = yaml.safe_load(stream)


def pytest_configure(config: pytest.config.Config) -> None:
    """
    Register custom markers to avoid pytest warnings.

    :param config: the pytest config object
    """
    all_tags: Set[str] = cast(Set[str], set()).union(*_testbeds.values())
    for tag in all_tags:
        config.addinivalue_line("markers", f"needs_{tag}")


def pytest_addoption(parser: pytest.config.ArgumentParser) -> None:
    """
    Pytest hook; implemented to add the `--testbed` option, used to specify the context
    in which the test is running. This could be used, for example, to skip tests that
    have requirements not met by the context.

    :param parser: the command line options parser
    """
    parser.addoption(
        "--testbed",
        choices=_testbeds.keys(),
        default="test",
        help="Specify the testbed on which the tests are running.",
    )


def pytest_collection_modifyitems(
    config: pytest.config.Config, items: List[pytest.Item]
) -> None:
    """
    Modify the list of tests to be run, after pytest has collected them.

    This hook implementation skips tests that are marked as needing some
    tag that is not provided by the current test context, as specified
    by the "--testbed" option.

    For example, if we have a hardware test that requires the presence
    of a real TPM, we can tag it with "@needs_tpm". When we run in a
    "test" context (that is, with "--testbed test" option), the test
    will be skipped because the "test" context does not provide a TPM.
    But when we run in "pss" context, the test will be run because the
    "pss" context provides a TPM.

    :param config: the pytest config object
    :param items: list of tests collected by pytest
    """
    testbed = config.getoption("--testbed")
    available_tags = _testbeds.get(testbed, set())

    prefix = "needs_"
    for item in items:
        needs_tags = set(
            tag[len(prefix) :]  # noqa: E203
            for tag in item.keywords
            if tag.startswith(prefix)
        )
        unmet_tags = list(needs_tags - available_tags)
        if unmet_tags:
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        f"Testbed '{testbed}' does not meet test needs: "
                        f"{unmet_tags}."
                    )
                )
            )


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
