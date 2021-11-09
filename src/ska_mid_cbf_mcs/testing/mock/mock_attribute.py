# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Ported from the SKA Low MCCS project: 
# https://gitlab.com/ska-telescope/ska-low-mccs/-/blob/main/src/ska_low_mccs/testing/mock/mock_device.py
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements infrastructure for mocking tango devices."""

from __future__ import annotations  # allow forward references in type hints

from typing import Any, Callable
import unittest.mock
import tango


__all__ = ["MockAttributeBuilder"]


class MockAttributeBuilder:
    """This module implements a mock builder for tango device attributes."""

    def __init__(
        self: MockAttributeBuilder,
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
        self._value = None

    def add_value(self: MockAttributeBuilder, value: Any) -> None:
        """
        Tell this builder to build mocks with a given value.

        :param value: the value of the attribute property
        """
        self._value = value

    def add_property(self: MockAttributeBuilder, name: str, value: Any) -> None:
        """
        Tell this builder to build mocks with a given attribute property.

        :param name: name of the attribute property
        :param value: the value of the attribute property
        """
        self._configuration[name] = value

    def _setup_get_property(
        self: MockAttributeBuilder, mock_attribute: unittest.mock.Mock
    ) -> None:
        """
        Set up property reads for a mock device.

        Tango allows attributes to be read via a high-level API
        (``device.voltage``) or a low-level API
        (`device.get_property("voltage"`). This method sets that up.

        :param mock_attribute: the mock being set up
        """

        def _mock_get_property(
            name: str, *args: Any, **kwargs: Any
        ) -> tango.DbData:
            """
            Mock side-effect for get_property method, which reads the
            property value and packs it into a
            :py:class:`tango.DeviceAttribute`.

            :param name: the name of the property
            :param args: positional args to ``get_property``
            :param kwargs: keyword args to ``get_property``

            :returns: a :py:class:`tango.DbData` A list of the
                device properties
            """

            return getattr(mock_attribute, name)

        mock_attribute.get_property.side_effect = _mock_get_property

    def _setup_subscribe_event(
        self: MockAttributeBuilder, mock_attribute: unittest.mock.Mock
    ) -> None:
        """
        Set up subscribe_event for a mock device.

        All the mock device is set up to do is to call the callback one
        time.

        :param mock_attribute: the mock being set up
        """

        def _mock_subscribe_event(
            event_type: tango.EventType,
            callback: Callable[[tango.EventData], None],
            stateless: bool,
        ) -> None:  # TODO: should be int
            """
            Mock side-effect for subscribe_event method.

            At present this method simply calls the provided callback
            with the current value of the attribute if it exists. It
            doesn't actually support publishing change events.

            :param event_type: type of the event being subscribed to
            :param callback: a callback to call
            :param stateless: whether this is a stateless subscription
            """
            mock_event_data = unittest.mock.Mock()
            mock_event_data.err = False
            mock_event_data.attr_value.name = "mockAttribute"
            mock_event_data.attr_value.value = type(self._value)()
            mock_event_data.attr_value.quality = tango.AttrQuality.ATTR_VALID
            callback(mock_event_data)

        mock_attribute.subscribe_event.side_effect = _mock_subscribe_event

    def __call__(self: MockAttributeBuilder) -> unittest.mock.Mock:
        """
        Call method for this builder: builds and returns a mock object.

        :return: a mock object
        """
        mock_attribute = self._from_factory()

        mock_attribute.configure_mock(**self._configuration)

        self._setup_get_property(mock_attribute)
        self._setup_subscribe_event(mock_attribute)
        return mock_attribute
