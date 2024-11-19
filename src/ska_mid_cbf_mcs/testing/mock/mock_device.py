# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Ported from the SKA Low MCCS project:
# https://gitlab.com/ska-telescope/mccs/ska-low-mccs-common/-/blob/main/src/ska_low_mccs_common/testing/
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements infrastructure for mocking tango devices."""

from __future__ import annotations  # allow forward references in type hints

import logging
import time
import unittest.mock
from threading import Thread
from typing import Callable

import tango
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.testing.mock.mock_command import MockCommand

__all__ = ["MockDeviceBuilder"]


class MockDeviceBuilder:
    """This module implements a mock builder for tango devices."""

    def __init__(
        self: MockDeviceBuilder,
        from_factory: type[unittest.mock.Mock] = unittest.mock.Mock,
    ) -> None:
        """
        Create a new instance.

        :param from_factory: an optional factory from which to draw the
            original mock
        """
        self.logger = logging.getLogger(__name__)
        self._from_factory = from_factory

        self._return_values: dict[str, any] = {}
        self._configuration: dict[str, any] = {}
        self._lrc_return_values: dict[str, any] = {}

    def add_attribute(self: MockDeviceBuilder, name: str, value: any) -> None:
        """
        Tell this builder to build mocks with a given attribute.

        TODO: distinguish between read-only and read-write attributes

        :param name: name of the attribute
        :param value: the value of the attribute
        """
        self._configuration[name] = value

    def add_property(self: MockDeviceBuilder, name: str, value: any) -> None:
        """
        Tell this builder to build mocks with a given device property.

        :param name: name of the device property
        :param value: the value of the device property
        """
        self._configuration[name] = value

    def add_command(
        self: MockDeviceBuilder,
        name: str,
        return_value: any,
    ) -> None:
        """
        Tell this builder to build mocks with a specified command that returns the
        provided value.

        :param name: name of the command
        :param return_value: what the command should return
        """
        self._return_values[name] = return_value

    def add_result_command(
        self: MockDeviceBuilder,
        name: str,
        result_code: ResultCode,
        message: str = "Mock information-only message",
    ) -> None:
        """
        Tell this builder to build mocks with a specified command that returns
        (ResultCode, [message, message_uid]) or (ResultCode, message) tuples as
        required.

        :param name: the name of the command
        :param result_code: the
            :py:class:`ska_tango_base.commands.ResultCode` that the
            command should return
        :param message: an information-only message for the command to
            return
        """
        self.add_command(name, [[result_code], [message]])

    def set_state(self: MockDeviceBuilder, state: tango.DevState) -> None:
        """
        Tell this builder to build mocks with the state set as specified.

        :param state: the state of the mock
        """
        self.add_command("state", state)
        self.add_command("State", state)

    def add_lrc(
        self: MockDeviceBuilder,
        name: str,
        queued: bool,
        result_code: ResultCode = None,
        message: str = None,
        attr_values: dict[str, any] = None,
        sleep_time_s: int = 0,
    ) -> None:
        """
        Tell this builder to build mocks with a specified long-running command that
        returns ([ResultCode], [command_id]).

        The `result_code` and `message` parameters are necessary to push an expected
        change to the `longRunningCommandResult` attribute, while `attr_values`
        can be used to supply further attribute change events that might be expected
        during the mocked LRC.
        As a helpful standard, `attr_values` can at baseline be a dictionary with
        an empty or None value for `longRunningCommandResult`, e.g.

        ```
        builder = MockDeviceBuilder()
        builder.add_lrc(
            name="On",
            result_code=ResultCode.OK,
            message="On completed OK",
            queued=True,
            attr_values={"longRunningCommandResult": ""},
        )
        ```

        :param name: the name of the command
        :param queued: if True, return ResultCode.QUEUED, if False, return ResultCode.REJECTED
        :param result_code: the
            :py:class:`ska_tango_base.commands.ResultCode` that the
            command should return
        :param message: an information-only message for the command to
            return
        :param attr_values: dict containing list of attributes and values to push
            events for in a given LRC
        :param sleep_time_s: sleep time in seconds to wait before pushing change event
        """
        if attr_values is None:
            attr_values = dict()
        self._lrc_return_values[name] = {
            "name": name,
            "queued": queued,
            "result_code": result_code,
            "message": message,
            "attr_values": attr_values,
            "sleep_time_s": sleep_time_s,
        }

    def _setup_read_attribute(
        self: MockDeviceBuilder, mock_device: unittest.mock.Mock
    ) -> None:
        """
        Set up attribute reads for a mock device.

        Tango allows attributes to be read via a high-level API
        (``device.voltage``) or a low-level API
        (`device.read_attribute("voltage"`). This method sets that up.

        :param mock_device: the mock being set up
        """

        def _mock_read_attribute(
            name: str, *args: any, **kwargs: any
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
                mock_device.state()
                if name == "state"
                else getattr(mock_device, name)
            )
            mock_attribute.quality = tango.AttrQuality.ATTR_VALID
            return mock_attribute

        mock_device.read_attribute.side_effect = _mock_read_attribute

    def _setup_get_property(
        self: MockDeviceBuilder, mock_device: unittest.mock.Mock
    ) -> None:
        """
        Set up property reads for a mock device.

        :param mock_device: the mock being set up
        """

        def _mock_get_property(
            name: str, *args: any, **kwargs: any
        ) -> tango.DbData:
            """
            Mock side-effect for get_property method, which reads the
            property value and packs it into a
            :py:class:`tango.DbData`.

            :param name: the name of the property
            :param args: positional args to ``get_property``
            :param kwargs: keyword args to ``get_property``

            :returns: a :py:class:`tango.DbData` A list of the
                device properties
            """

            return getattr(mock_device, name)

        mock_device.get_property.side_effect = _mock_get_property

    def _setup_command_inout(
        self: MockDeviceBuilder, mock_device: unittest.mock.Mock
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

        :param mock_device: the mock being set up
        """

        def _mock_command_inout(name: str, *args: str, **kwargs: str) -> any:
            """
            Mock side-effect for command_inout method.

            :param name: the name of the command
            :param args: positional args to ``command_inout``
            :param kwargs: keyword args to ``command_inout``

            :return: the specified return value for the command
            """
            return getattr(mock_device, name)()

        mock_device.command_inout.side_effect = _mock_command_inout

        def _mock_command_inout_asynch(
            name: str, *args: str, **kwargs: str
        ) -> str:
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

        mock_device.command_inout_asynch.side_effect = (
            _mock_command_inout_asynch
        )

        def _mock_command_inout_reply(
            asynch_id: str, *args: str, **kwargs: str
        ) -> any:
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
            return getattr(mock_device, command_name)()

        mock_device.command_inout_reply.side_effect = _mock_command_inout_reply

    def _setup_change_events(
        self: MockDeviceBuilder, mock_device: unittest.mock.Mock
    ) -> None:
        """
        Set up attribute change events for a mock device.

        All the mock device is set up to do is to call the callback one
        time. Further calls must be made manually in the test using
        mock_device.mock_event

        :param mock_device: the mock being set up
        """

        def _mock_event(
            attr_name: str,
            attr_value: any,
            callback: Callable[[tango.EventData], None],
            attr_quality: tango.AttrQuality = tango.AttrQuality.ATTR_VALID,
            attr_err: bool = False,
            sleep_time_s: int = 0,
        ) -> None:
            """
            Mock a Tango change event callback

            :param attr_name: name of the attribute for which
                events are subscribed
            :param attr_value: attribute value to push
            :param callback: a callback to call
            :param attr_quality: attribute quality to push
            :param attr_err: attribute error to push
            :param sleep_time_s: sleep time in seconds to wait before pushing
                change event
            """
            mock_event_data = unittest.mock.Mock()
            mock_event_data.device.dev_name = mock_device.dev_name
            mock_event_data.err = attr_err
            mock_event_data.attr_value.name = attr_name
            mock_event_data.attr_value.value = attr_value
            mock_event_data.attr_value.quality = attr_quality

            # Invoke callback asynchronously
            time.sleep(sleep_time_s)
            Thread(target=callback, args=(mock_event_data,)).start()

        def _mock_subscribe_event(
            attr_name: str,
            event_type: tango.EventType,
            cb_or_queuesize: Callable[[tango.EventData], None],
            stateless: bool = False,
        ) -> int:
            """
            Mock side-effect for subscribe_event method.

            This method simply calls the provided callback with the current
            value of the attribute if it exists. Mocking change event callbacks
            with the mock device must be done during the test scenario using
            `mock_device.change_event_callback`

            :param attr_name: name of the attribute for which
                events are subscribed
            :param event_type: type of the event being subscribed to
            :param cb_or_queuesize: a callback to call
            :param stateless: whether this is a stateless subscription
            :return: a unique event subscription identifier
            :rtype: int
            """
            attr_value = (
                mock_device.state()
                if attr_name == "state"
                else getattr(mock_device, attr_name)
            )

            # Generate a unique event_subscription_id
            sub_id = int(time.time_ns())

            # Generate the subscription event
            _mock_event(attr_name, attr_value, cb_or_queuesize)

            # Store the callback, to be used by MockCommand later
            mock_device.attr_change_event_callbacks[
                attr_name
            ] = cb_or_queuesize

            return sub_id

        def _mock_unsubscribe_event(event_id: int) -> None:
            """
            Mock side-effect for unsubscribe_event method.

            :param event_id: event ID to unsubscribe from
            """
            self.logger.debug(f"Unsubscribe from event ID {event_id}")
            return None

        mock_device.subscribe_event.side_effect = _mock_subscribe_event
        mock_device.unsubscribe_event.side_effect = _mock_unsubscribe_event
        mock_device.mock_event.side_effect = _mock_event

    def __call__(
        self: MockDeviceBuilder,
        dev_name: str = "",
    ) -> unittest.mock.Mock:
        """
        Call method for this builder: builds and returns a mock object.

        :param dev_name: name for the mock object
        :return: a mock object
        """
        self.logger.debug(f"Creating mock device {dev_name}")

        mock_device = self._from_factory()
        mock_device.attr_change_event_callbacks = {}

        self._return_values["dev_name"] = dev_name

        for command_name, return_value in self._return_values.items():
            self.logger.debug(
                f"Command: {command_name}\n" + f"Return Value: {return_value}"
            )
            self._configuration[command_name] = MockCommand(
                return_value=return_value
            )

        for command_name, return_value in self._lrc_return_values.items():
            self.logger.debug(
                f"LRC: {command_name}\n" + f"Return Value: {return_value}"
            )
            self._configuration[command_name] = MockCommand(
                return_value=return_value, is_lrc=True, mock_device=mock_device
            )

        mock_device.configure_mock(**self._configuration)

        self._setup_read_attribute(mock_device)
        self._setup_get_property(mock_device)
        self._setup_change_events(mock_device)
        self._setup_command_inout(mock_device)

        return mock_device
