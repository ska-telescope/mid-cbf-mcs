# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements a base attribute proxy for MCS device attributes."""

from __future__ import annotations  # allow forward references in type hints

__all__ = ["CbfAttributeProxy"]

import logging
import threading
from typing import Any, Callable, Optional, Type
from typing_extensions import TypedDict
import warnings

import backoff
import tango
from tango import DevFailed, DevState, AttrQuality

# type for the "details" dictionary that backoff calls its callbacks with
BackoffDetailsType = TypedDict("BackoffDetailsType", {"args": list, "elapsed": float})
ConnectionFactory = Callable[[str], tango.AttributeProxy]


class CbfAttributeProxy:
    """
    This class implements a base attribute proxy for MCS device attributes.

    At present it supports:

    * deferred connection: we can create the proxy without immediately
      trying to connect to the proxied attribute.
    * a :py:meth:``connect`` method, for establishing that connection
      later
    * Ability to subscribe to change events via the
      :py:meth:``add_change_event_callback`` method.
    """

    _default_connection_factory = tango.AttributeProxy

    @classmethod
    def set_default_connection_factory(
        cls: Type[CbfAttributeProxy], connection_factory: ConnectionFactory
    ) -> None:
        """
        Set the default connection factory for this class.

        This is super useful for unit testing: we can mock out
        :py:class:`tango.AttributeProxy` altogether, by simply setting this
        class's default connection factory to a mock factory.

        :param connection_factory: default factory to use to establish
            a connection to the device
        """
        cls._default_connection_factory = connection_factory

    def __init__(
        self: CbfAttributeProxy,
        fqdn: str,
        logger: logging.Logger,
        connect: bool = True,
        connection_factory: Optional[ConnectionFactory] = None,
        pass_through: bool = True,
    ) -> None:
        """
        Create a new instance.

        :param fqdn: fqdn of the device attribute to be proxied
        :param logger: a logger for this proxy to use
        :param connection_factory: how we obtain a connection to the
            device attribute we are proxying. By default this is
            :py:class:`tango.AttributeProxy`, but occasionally this needs
            to be changed. For example, when testing against a
            :py:class:`tango.test_context.MultiDeviceTestContext`.
        :param connect: whether to connect immediately to the attribute. If
            False, then the attribute may be connected later by calling the
            :py:meth:`.connect` method.
        :param pass_through: whether to pass unrecognised attribute
            accesses through to the underlying connection. Defaults to
            ``True`` but this will likely change in future once our
            proxies are more mature.
        """
        # Directly accessing object dictionary because we are overriding
        # setattr and don't want to infinitely recurse.
        self.__dict__["_fqdn"] = fqdn
        self.__dict__["_logger"] = logger
        self.__dict__["_connection_factory"] = (
            connection_factory or CbfAttributeProxy._default_connection_factory
        )
        self.__dict__["_pass_through"] = pass_through
        self.__dict__["_attribute"] = None

        self.__dict__["_change_event_lock"] = threading.Lock()
        self.__dict__["_change_event_subscription_ids"] = {}
        self.__dict__["_change_event_callback"] = []

        if connect:
            self.connect()

    def connect(self: CbfAttributeProxy, max_time: float = 120.0) -> None:
        """
        Establish a connection to the device attribute that we want to proxy.

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
            elapsed = details["elapsed"]
            self._logger.warning(
                f"Gave up trying to connect to attribute {fqdn} after "
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
            connection_factory: Callable[[str], tango.AttributeProxy], fqdn: str
        ) -> tango.AttributeProxy:
            """
            Attempt connection to a specified device attribute.

            Connection attribute use an exponential backoff-retry
            scheme in case of failure.

            :param connection_factory: the factory to use to establish
                the connection
            :param fqdn: the fully qualified domain name of the device attribute

            :return: a proxy for the device attribute
            """
            return _connect(connection_factory, fqdn)

        def _connect(
            connection_factory: Callable[[str], tango.AttributeProxy], fqdn: str
        ) -> tango.AttributeProxy:
            """
            Make a single attempt to connect to a device.

            :param connection_factory: the factory to use to establish
                the connection
            :param fqdn: the fully qualified domain name of the device attribute

            :return: a proxy for the device attribute
            """
            return connection_factory(fqdn)

        if max_time:
            self._attribute = _backoff_connect(self._connection_factory, self._fqdn)
        else:
            self._attribute = _connect(self._connection_factory, self._fqdn)

    def add_change_event_callback(
        self: CbfAttributeProxy,
        callback: Callable[[str, Any, AttrQuality], None],
        stateless: bool = True,
    ) -> int:
        """
        Register a callback for change events being pushed by the device attribute.

        :param callback: the function to be called when a change event
            arrives.
        :param stateless: whether to use Tango's stateless subscription
            feature
        """
        if callback not in self._change_event_subscription_id:
            self._change_event_callback = callback
            self._change_event_subscription_id = self._subscribe_change_event(stateless=stateless)
        else:
            self._change_event_callback.append(callback)
            self._call_callback(callback, self._read())
        return self._change_event_subscription_id

    @backoff.on_exception(backoff.expo, tango.DevFailed, factor=1, max_time=120)
    def _subscribe_change_event(
        self: CbfAttributeProxy, stateless: bool = False
    ) -> int:
        """
        Subscribe to a change event.

        Even though we already have an AttributeProxy to the device attribute
        that we want to subscribe to, it is still possible that the attribute is
        not ready, in which case subscription will fail and a
        :py:class:`tango.DevFailed` exception will be raised. Here, we
        attempt subscription in a backoff-retry, and only raise the
        exception one our retries are exhausted. (The alternative option
        of subscribing with "stateless=True" could not be made to work.)

        :param stateless: whether to use Tango's stateless subscription
            feature

        :return: the subscription id
        """
        return self._device.subscribe_event(
            tango.EventType.CHANGE_EVENT,
            self._change_event_received,
            stateless=stateless,
        )

    def _change_event_received(self: CbfAttributeProxy, event: tango.EventData) -> None:
        """
        Handle subscribe events from the Tango system with this callback.

        It in turn invokes all its own callbacks.

        :param event: an object encapsulating the event data.
        """
        # TODO: not sure if it is overkill to serialise change event
        # handling, but it seems like the safer way to go
        with self._change_event_lock:
            attribute_data = self._process_event(event)
            if attribute_data is not None:
                for callback in self._change_event_callbacks:
                    self._call_callback(callback, attribute_data)

    def _call_callback(
        self: CbfAttributeProxy,
        callback: Callable[[str, Any, AttrQuality], None],
        attribute_data: tango.DeviceAttribute,
    ) -> None:
        """
        Call the callback with unpacked attribute data.

        :param callback: function handle for the callback
        :param attribute_data: the attribute data to be unpacked and
            used to call the callback
        """
        callback(self._fqdn,
            attribute_data.name, attribute_data.value, attribute_data.quality)

    def _process_event(
        self: CbfAttributeProxy, event: tango.EventData
    ) -> Optional[tango.DeviceAttribute]:
        """
        Process a received event.

        Extract the attribute value from the event; or, if the event
        failed to carry an attribute value, read the attribute value
        directly.

        :param event: the received event

        :return: the attribute value data
        """
        if event.err:
            self._logger.warn(
                f"Received failed change event: error stack is {event.errors}."
            )
            return None
        elif event.attr_value is None:
            warning_message = (
                "Received change event with empty value. Falling back to manual "
                f"attribute read. Event.err is {event.err}. Event.errors is\n"
                f"{event.errors}."
            )
            warnings.warn(UserWarning(warning_message))
            self._logger.warn(warning_message)
            return self._read()
        else:
            return event.attr_value


    def _read(self: CbfAttributeProxy) -> Any:
        """
        Read an attribute manually.

        Used when we receive an event with empty attribute data.

        :param attribute_name: the name of the attribute to be read

        :return: the attribute value
        """
        return self._attribute.read()

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
    # def __del__(self: CbfAttributeProxy) -> None:
    #     """Cleanup before destruction."""
    #     for subscription_id in self._change_event_subscription_ids:
    #         self._attribute.unsubscribe_event(subscription_id)

    def __setattr__(self: CbfAttributeProxy, name: str, value: Any) -> None:
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
            if self._attribute is None:
                raise ConnectionError("CbfAttributeProxy has not connected yet.")
            setattr(self._attribute, name, value)

    def __getattr__(self: CbfAttributeProxy, name: str, default_value: Any = None) -> Any:
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
        if self._pass_through and self._attribute is not None:
            return getattr(self._attribute, name, default_value)
        elif default_value is not None:
            return default_value
        else:
            raise AttributeError(f"No such attribute: {name}")
