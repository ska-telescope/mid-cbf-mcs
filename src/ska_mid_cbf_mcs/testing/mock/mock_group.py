# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements infrastructure for mocking tango groups."""

from __future__ import annotations  # allow forward references in type hints

from typing import Any, Callable
import unittest.mock

import tango

from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable


__all__ = ["MockGroupBuilder"]


class MockGroupBuilder:
    """This module implements a mock builder for tango devices."""

    def __init__(
        self: MockGroupBuilder,
        from_factory: type[unittest.mock.Mock] = unittest.mock.Mock,
    ) -> None:
        """
        Create a new instance.

        :param from_factory: an optional factory from which to draw the
            original mock
        """
        self._from_factory = from_factory

        self._return_values: dict[str, Any] = {}
        self._configuration: dict[str, Any] = {}

    def add(self: MockGroupBuilder, fqdns: list[str]) -> None:
        """
        Tell this group builder to add the given device FQDNs.

        :param fqdns: list of device FQDNs to add to group
        """
        pass
    
    def remove(self: MockGroupBuilder, fqdns: list[str]) -> None:
        """
        Tell this group builder to remove the given device FQDNs.

        :param fqdns: list of device FQDNs to remove from the group
        """
        pass

    def add_attribute(self: MockGroupBuilder, name: str, value: Any) -> None:
        """
        Tell this builder to build mocks with a given attribute.

        TODO: distinguish between read-only and read-write attributes

        :param name: name of the attribute
        :param value: the value of the attribute
        """
        self._configuration[name] = value

    def add_command(self: MockGroupBuilder, name: str, return_value: Any) -> None:
        """
        Tell this builder to build mocks with a specified command that returns the
        provided value.

        :param name: name of the command
        :param return_value: what the command should return
        """
        self._return_values[name] = return_value

    def add_result_command(
        self: MockGroupBuilder,
        name: str,
        result_code: ResultCode,
        status: str = "Mock information-only message",
    ) -> None:
        """
        Tell this builder to build mocks with a specified command that returns
        (ResultCode, [message, message_uid]) or (ResultCode, message) tuples as
        required.

        :param name: the name of the command
        :param result_code: the
            :py:class:`ska_tango_base.commands.ResultCode` that the
            command should return
        :param status: an information-only message for the command to
            return
        """
        self.add_command(name, [[result_code], [status]])

    def set_state(self: MockGroupBuilder, state: tango.DevState) -> None:
        """
        Tell this builder to build mocks with the state set as specified.

        :param state: the state of the mock
        """
        self.add_command("state", state)

    def _setup_read_attribute(
        self: MockGroupBuilder, mock_group: unittest.mock.Mock
    ) -> None:
        """
        Set up attribute reads for a mock device.

        Tango allows attributes to be read via a high-level API
        (``device.voltage``) or a low-level API
        (`device.read_attribute("voltage"`). This method sets that up.

        :param mock_group: the mock being set up
        """

        def _mock_read_attribute(
            name: str, *args: Any, **kwargs: Any
        ) -> tango.DeviceAttribute:
            """
            Mock side-effect for read_attribute method, which reads the
            attribute value and packs it into a
            :py:class:`tango.DeviceAttribute`.

            :param name: the name of the attribute
            :param args: positional args to ``read_attribute``
            :param kwargs: keyword args to ``read_attribute``

            :returns: a :py:class:`tango.DeviceAttribute` object
                containing the attribute value
            """
            mock_attribute = unittest.mock.Mock()
            mock_attribute.name = name
            mock_attribute.value = (
                mock_group.state() if name == "state" else getattr(mock_group, name)
            )
            mock_attribute.quality = tango.AttrQuality.ATTR_VALID
            return mock_attribute

        mock_group.read_attribute.side_effect = _mock_read_attribute

    def _setup_command_inout(
        self: MockGroupBuilder, mock_group: unittest.mock.Mock
    ) -> None:
        """
        Set up command_inout for a mock device.

        Tango allows commands to be invoked via a high-level API
        (``device.Scan()``) or various low-level commands including the
        synchronous :py:class:`tango.DeviceProxy.command_inout` and the
        asynchronous pair
        :py:class:`tango.DeviceProxy.command_inout_asynch` and
        :py:class:`tango.DeviceProxy.command_inout_reply`. This method
        sets them up.

        :param mock_group: the mock being set up
        """

        def _mock_command_inout(name: str, *args: str, **kwargs: str) -> Any:
            """
            Mock side-effect for command_inout method.

            :param name: the name of the command
            :param args: positional args to ``command_inout``
            :param kwargs: keyword args to ``command_inout``

            :return: the specified return value for the command
            """
            return getattr(mock_group, name).return_value

        mock_group.command_inout.side_effect = _mock_command_inout

        def _mock_command_inout_asynch(name: str, *args: str, **kwargs: str) -> str:
            """
            Mock side-effect for command_inout_asynch method.

            This mock is set up to return the command name as the
            asynch_id, so that command_inout_reply can recover the name
            of the command.

            :param name: the name of the command
            :param args: positional args to ``command_inout_asynch``
            :param kwargs: keyword args to ``command_inout_asynch``

            :return: nominally the asynch_id, but here we mock that with
                the name of the command.
            """
            asynch_id = name
            return asynch_id

        mock_group.command_inout_asynch.side_effect = _mock_command_inout_asynch

        def _mock_command_inout_reply(asynch_id: str, *args: str, **kwargs: str) -> Any:
            """
            Mock side-effect for command_inout_reply method.

            The command_inout_asynch method has been mocked to return
            the command name as the asynch_id, so in this command we can
            use the asynch_id as the name of the command.

            :param asynch_id: here mocked to be the command name
            :param args: positional args to ``command_inout_reply``
            :param kwargs: keyword args to ``command_inout_reply``

            :return: the specified return value for the command
            """
            command_name = asynch_id
            return getattr(mock_group, command_name).return_value

        mock_group.command_inout_reply.side_effect = _mock_command_inout_reply

    def __call__(self: MockGroupBuilder) -> unittest.mock.Mock:
        """
        Call method for this builder: builds and returns a mock object.

        :return: a mock object
        """
        mock_group = self._from_factory()

        for command in self._return_values:
            self._configuration[command] = MockCallable(
                return_value=self._return_values[command]
            )

        mock_group.configure_mock(**self._configuration)

        self._setup_read_attribute(mock_group)
        self._setup_command_inout(mock_group)
        return mock_group
