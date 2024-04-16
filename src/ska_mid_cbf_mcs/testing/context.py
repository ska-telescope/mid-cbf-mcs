"""This module provides support for tango testing contexts."""

from __future__ import annotations

import unittest.mock
from types import TracebackType
from typing import Any, Optional, Type, Union

import tango
import tango.server
import tango.test_context
from ska_tango_testing import context
from typing_extensions import Literal, Protocol

# PROXY WRAPPERS START
# TODO: Remove proxy wrappers once pytango issue
# https://gitlab.com/tango-controls/pytango/-/issues/459 has been fixed.


class _GroupFactory:  # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        self.factory = tango.Group

    def __call__(self, name: str, *args: Any, **kwargs: Any) -> tango.Group:
        return self.factory(name, *args, **kwargs)

    # TODO: add/remove?


DeviceProxy = context._DeviceProxyFactory()
Group = _GroupFactory()

"""
Drop-in replacements for :py:class:`tango.DeviceProxy`and :py:class:`tango.Group`.

There is a known bug in :py:class:`tango.test_context.MultiDeviceTestContext`
for which the workaround is a patch to :py:class:`tango.DeviceProxy`.
This drop-in replacement makes it possible for
:py:class:`~ska_tango_testing.context.ThreadedTestTangoContextManager`
to apply this patch. Until the bug is fixed, all production code that
will be tested in that context must use this class instead of
:py:class:`tango.DeviceProxy`.

(For more information, see
https://gitlab.com/tango-controls/pytango/-/issues/459.)
"""
# PROXY WRAPPERS END


class TTCMExt(context.ThreadedTestTangoContextManager):
    """
    An extension of the ska_tango_testing ThreadedTestTangoContextManager.
    Adds factories for group proxies.
    """

    def __init__(self) -> None:
        """Initialise a new instance."""
        self._device_info_by_class: dict[
            Union[str, Type[tango.server.Device]], list[dict[str, Any]]
        ] = {}
        self._context: Optional[TTCMExt._TangoContext] = None
        self._mocks: dict[str, unittest.mock.Mock] = {}

    def add_mock_device(
        self: TTCMExt,
        device_name: str,
        device_mock: unittest.mock.Mock,
    ) -> None:
        """
        Register a mock at a given device name.

        Registering this mock means that when an attempts is made to
        create a `ska_mid_cbf_mcs.context.DeviceProxy` to that device name, this mock is
        returned instead.

        :param device_name: name of the device for which the mock is to
            be registered.
        :param device_mock: the mock to be registered at this name.
        """
        self._mocks[device_name] = device_mock

    def add_mock_group(
        self: TTCMExt,
        group_name: str,
        group_mock: unittest.mock.Mock,
    ) -> None:
        """
        Register a mock for a given group name.

        Registering this mock means that when an attempts is made to create a
        `ska_mid_cbf_mcs.context.Group` with that group name,
        this mock is returned instead.

        :param group_name: name of the group for which the mock is to
            be registered.
        :param group_mock: the mock to be registered at this name.
        """
        self._mocks[group_name] = group_mock

    class TCExt(context.ThreadedTestTangoContextManager._TangoContext):
        """Tango testing context class; sets the default factories for proxy types."""

        def __init__(
            self: TTCMExt.TCExt,
            device_info: list[dict[str, Any]],
            mocks: dict[str, unittest.mock.Mock],
        ) -> None:
            self._context: Optional[tango.test_context.MultiDeviceTestContext]
            if device_info:
                self._context = tango.test_context.MultiDeviceTestContext(
                    device_info,
                    process=False,
                    daemon=True,
                )
            else:
                self._context = None
            self._mocks = mocks

        def __enter__(self: TTCMExt.TCExt) -> context.TangoContextProtocol:
            Group.factory = self._group_factory
            return super().__enter__()

        def _group_factory(
            self: TTCMExt.TCExt, name: str, *args: Any, **kwargs: Any
        ) -> tango.Group:
            if name in self._mocks:
                return self._mocks[name]
            if self._context is None:
                raise KeyError(
                    f"Test context has no mock for {name}, "
                    "and no devices at all."
                )
            return tango.Group(
                self._context.get_device_access(name), *args, **kwargs
            )

    def __enter__(self: TTCMExt) -> context.TangoContextProtocol:
        """
        Enter the context.

        The context is a :py:class:`tango.test_context.MultiDeviceTestContext`,
        which has a known bug that forces us to patch `tango.DeviceProxy`.

        :return: a proxy to the device under test.
        """
        device_info = [
            {"class": class_name, "devices": devices}
            for class_name, devices in self._device_info_by_class.items()
        ]
        self._context = self.TCExt(device_info=device_info, mocks=self._mocks)
        return self._context.__enter__()
