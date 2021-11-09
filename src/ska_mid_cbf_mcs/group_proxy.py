# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements a base group device proxy for MCS devices."""

from __future__ import annotations  # allow forward references in type hints

__all__ = ["CbfGroupProxy"]

import logging
import threading
from typing import Any, Callable, Optional, Type, List
from typing_extensions import TypedDict
import warnings
import backoff

import tango
from tango import DevFailed, DevState, AttrQuality

# type for the "details" dictionary that backoff calls its callbacks with
BackoffDetailsType = TypedDict(
    "BackoffDetailsType", {"args": list, "elapsed": float}
)
ConnectionFactory = Callable[[str], tango.Group]


class CbfGroupProxy:
    """
    This class implements a base group proxy for MCS devices.

    Currently only used for providing mock group connections to devices during
    unit testing.
    """

    _default_connection_factory = tango.Group

    @classmethod
    def set_default_connection_factory(
        cls: Type[CbfGroupProxy], group_connection_factory: ConnectionFactory
    ) -> None:
        """
        Set the default connection factory for this class.

        This is super useful for unit testing: we can mock out
        :py:class:`tango.DeviceProxy` altogether, by simply setting this
        class's default connection factory to a mock factory.

        :param group_connection_factory: default factory to use to establish
            a connection to the device
        """
        cls._default_connection_factory = group_connection_factory

    def __init__(
        self: CbfGroupProxy,
        name: str,
        logger: logging.Logger,
        group_connection_factory: Optional[ConnectionFactory] = None,
        pass_through: bool = True,
    ) -> None:
        """
        Create a new instance.

        :param logger: a logger for this proxy to use
        :param group_connection_factory: how we obtain a connection to the
            device we are proxying. By default this is
            :py:class:`tango.Group`, but occasionally this needs
            to be changed. For example, when testing against a
            :py:class:`tango.test_context.MultiDeviceTestContext`, we
            obtain connections to the devices under test via
            ``test_context.get_device(fqdn)``.
        :param pass_through: whether to pass unrecognised attribute
            accesses through to the underlying connection. Defaults to
            ``True`` but this will likely change in future once our
            proxies are more mature.
        """
        # Directly accessing object dictionary because we are overriding
        # setattr and don't want to infinitely recurse.
        self.__dict__["_name"] = name
        self.__dict__["_fqdns"] = []
        self.__dict__["_logger"] = logger
        self.__dict__["_group_connection_factory"] = (
            group_connection_factory or 
            CbfGroupProxy._default_connection_factory
        )
        self.__dict__["_pass_through"] = pass_through
        self.__dict__["_group"] = None

        self.__dict__["_change_event_lock"] = threading.Lock()
        self.__dict__["_change_event_subscription_ids"] = {}
        self.__dict__["_change_event_callbacks"] = {}


    def add(self: CbfGroupProxy,
        fqdns: List[str],
        max_time: float = 120.0
    ) -> None:
        """
        Adds connections to the devices that we want to proxy to the group.

        :param fqdn: FQDNs of the devices to be proxied
        :param max_time: the maximum time, in seconds, to wait for a
            connection to be established. The default is 120 i.e. two
            minutes. If set to 0 or None, a single connection attempt is
            made, and the call returns immediately.
        """

        def _on_giveup_connect(details: BackoffDetailsType) -> None:
            """
            Give up trying to make a connection to the device.

            :param details: a dictionary providing call context, such as
                the call args and the elapsed time
            """
            fqdn = details["args"][1]
            self.__dict__["_fqdns"].remove(fqdn)
            elapsed = details["elapsed"]
            self._logger.warning(
                f"Gave up trying to connect to device {fqdn} after "
                f"{elapsed} seconds."
            )

        @backoff.on_exception(
            backoff.expo,
            DevFailed,
            on_giveup=_on_giveup_connect,
            factor=1,
            max_time=max_time,
        )
        def _backoff_connect(
            group_connection_factory: Callable[[str], tango.Group],
        ) -> tango.Group:
            """
            Attempt connection to a specified device.

            Connection attribute use an exponential backoff-retry
            scheme in case of failure.

            :param group_connection_factory: the factory to use to establish
                the connection
            :param fqdn: the fully qualified device name of the device

            :return: a proxy for the device
            """
            return _connect(group_connection_factory)

        def _connect(
            group_connection_factory: Callable[[str], tango.Group],
        ) -> tango.Group:
            """
            Make a single attempt to connect to a device.

            :param group_connection_factory: the factory to use to establish
                the connection
            :param fqdn: the fully qualified device name of the device

            :return: a proxy for the device
            """
            group = group_connection_factory(self._name)
            group.add(fqdns)
            return group

        if self._group == None:
            if max_time:
                self.__dict__["_group"] = _backoff_connect(self._group_connection_factory)
            else:
                self.__dict__["_group"] = _connect(self._group_connection_factory)
        else:
            self.__dict__["_group"].add(fqdns)

        self.__dict__["_fqdns"].extend(fqdns)


    def remove(self: CbfGroupProxy, fqdns: List[str]) -> None:
        """
        Remove a device from the group.

        :param fqdn: FQDN of the device to be proxied.
        """
        for fqdn in fqdns:
            self.__dict__["_fqdns"].remove(fqdn)
            self.__dict__["_group"].remove(fqdn)

    def remove_all(self: CbfGroupProxy) -> None:
        """
        Remove all devices from the group.
        """
        self.remove(self._fqdns)


    def check_initialised(self: CbfGroupProxy, max_time: float = 120.0) -> bool:
        """
        Check that the device has completed initialisation.

        That is, check that the device is no longer in state INIT.

        :param max_time: the (optional) maximum time, in seconds, to
            wait for the device to complete initialisation. The default
            is 120.0 i.e. two minutes. If set to 0 or None, the device
            is checked once and the call returns immediately.

        :return: whether the device is initialised yet
        """

        def _on_giveup_check_initialised(details: BackoffDetailsType) -> None:
            """
            Give up waiting for the device to complete initialisation.

            :param details: a dictionary providing call context, such as
                the call args and the elapsed time
            """
            elapsed = details["elapsed"]
            self._logger.warning(
                f"Gave up waiting for the device ({self._fqdn}) to complete "
                f"initialisation after {elapsed} seconds."
            )

        @backoff.on_predicate(
            backoff.expo,
            on_giveup=_on_giveup_check_initialised,
            factor=1,
            max_time=max_time,
        )
        def _backoff_check_initialised(device: tango.DeviceProxy) -> bool:
            """
            Check that the device has completed initialisation.

            That is, check that the device is no longer in
            :py:const:`tango.DevState.INIT`. This check is performed
            in an exponential backoff-retry loop.

            :param device: the device to be checked

            :return: whether the device has completed initialisation
            """
            return _check_initialised(device)

        def _check_initialised(device: tango.DeviceProxy) -> bool:
            """
            Check that the device has completed initialisation.

            That is, check that the device is no longer in
            :py:const:`tango.DevState.INIT`.

            Checking that a device has initialised means calling its
            `state()` method, and even after the device returns a
            response from a ping, it might still raise an exception in
            response to reading device state
            (``"BAD_INV_ORDER_ORBHasShutdown``). So here we catch that
            exception.

            This method only performs a single check, and returns
            immediately. To check for initialisation in an exponential
            backoff-retry loop, use
            :py:meth:`._backoff_check_initialised`.

            :param device: the device to be checked

            :return: whether the device has completed initialisation
            """
            try:
                return device.state() != DevState.INIT
            except DevFailed:
                self._logger.debug(
                    "Caught a DevFailed exception while checking that the device has "
                    "initialised. This is most likely a 'BAD_INV_ORDER_ORBHasShutdown "
                    "exception triggered by the call to state()."
                )
                return False

        if max_time:
            return _backoff_check_initialised(self._group)
        else:
            return _check_initialised(self._group)

    def _read(self: CbfGroupProxy, attribute_name: str) -> Any:
        """
        Read an attribute manually.

        Used when we receive an event with empty attribute data.

        :param attribute_name: the name of the attribute to be read

        :return: the attribute value
        """
        return self._group.read_attribute(attribute_name)

    # TODO: This method is commented out because it is implicated in our segfault
    # issues:
    # a) We know that any time we access Tango from a python-native thread, we have to
    #    wrap it in ``with tango.EnsureOmniThread():`` to avoid segfaults.
    # b) Although we don't explicitly launch a thread here, the ``__del__`` method is
    #    run on the python garbage collection thread, which is a python-native thread!
    # c) Wrapping a __del__ method in ``with tango.EnsureOmniThread():`` seems fraught
    #    with danger of re-entrancy / deadlock.
    # Therefore this method is commented out for now. Unfortunately this means we don't
    # clean up properly after ourselves, so we should find a better solution if
    # possible.
    #
    # def __del__(self: CbfGroupProxy) -> None:
    #     """Cleanup before destruction."""
    #     for subscription_id in self._change_event_subscription_ids:
    #         self._group.unsubscribe_event(subscription_id)

    def __setattr__(self: CbfGroupProxy, name: str, value: Any) -> None:
        """
        Handle the setting of attributes on this object.

        If the name matches an attribute that this object already has,
        we update it. But we refuse to create any new attributes.
        Instead, if we're in pass-through mode, we pass the setattr
        down to the underlying connection.

        :param name: the name of the attribute to be set
        :param value: the new value for the attribute

        :raises ConnectionError: if the device is not connected yet.
        """
        if name in self.__dict__:
            self.__dict__[name] = value
        elif self._pass_through:
            if self._group is None:
                raise ConnectionError("CbfGroupProxy has not connected yet.")
            setattr(self._group, name, value)

    def __getattr__(self: CbfGroupProxy, name: str, default_value: Any = None) -> Any:
        """
        Handle any requested attribute not found in the usual way.

        If this proxy is in pass-through mode, then we try to get this
        attribute from the underlying proxy.

        :param name: name of the requested attribute
        :param default_value: value to return if the attribute is not
            found

        :raises AttributeError: if neither this class nor the underlying
            proxy (if in pass-through mode) has the attribute.

        :return: the requested attribute
        """
        if self._pass_through and self._group is not None:
            return getattr(self._group, name, default_value)
        elif default_value is not None:
            return default_value
        else:
            raise AttributeError(f"No such attribute: {name}")

