from queue import Queue
from typing import Any

import tango
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup


def change_event_subscriber(
    dut: tango.DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
    change_event_attr_list: list,
) -> dict:
    # subscribe to and provide event IDs for all specified attributes
    attr_event_ids = {}
    for event_type in change_event_attr_list:
        attr_event_ids[event_type] = dut.subscribe_event(
            event_type,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[event_type],
        )
        # assert against first empty change event received
        change_event_callbacks.assert_change_event(event_type, Anything)
    return attr_event_ids


def change_event_unsubscriber(
    dut: tango.DeviceProxy, attr_event_ids: dict
) -> None:
    # unsubsubscribe from events for all specified event IDs
    for key, value in attr_event_ids.items():
        attr_event_ids[key] = dut.unsubscribe_event(value)


class LRCAttributesStore:
    """Utility class to keep track of LRC attribute changes."""

    def __init__(self) -> None:
        """Create the queues."""
        self.queues = {}
        self.event_name_map = {}
        for attribute in [
            "longRunningCommandsInQueue",
            "longRunningCommandStatus",
            "longRunningCommandProgress",
            "longRunningCommandIDsInQueue",
            "longRunningCommandResult",
        ]:
            self.queues[attribute] = Queue()
            self.event_name_map[attribute.lower()] = attribute

    def store_push_event(self, attribute_name: str, value: Any):
        """Store attribute changes as they change.

        :param attribute_name: a valid LCR attribute
        :type attribute_name: str
        :param value: The value of the attribute
        :type value: Any
        """
        print(f"Storing {value} in {attribute_name} queue")
        assert attribute_name in self.queues
        self.queues[attribute_name].put_nowait(value)

    def push_event(self, ev: tango.EventData):
        """Store attribute events

        :param ev: Tango event
        :type ev: tango.EventData
        """
        print(f"ev: {ev}")
        print(f"a: {ev.attr_value}")
        print(f"b: {ev.attr_value.name}")
        attribute_name = ev.attr_name.split("/")[-1].replace("#dbase=no", "")
        if attribute_name in self.event_name_map:
            if ev.attr_value:
                self.queues[self.event_name_map[attribute_name]].put_nowait(
                    ev.attr_value.value
                )

    def get_attribute_value(
        self, attribute_name: str, fetch_timeout: float = 2.0
    ):
        """Read a value from the queue.

        :param attribute_name: a valid LCR attribute
        :type attribute_name: str
        :param fetch_timeout: How long to wait for a event, defaults to 2.0
        :type fetch_timeout: float, optional
        :return: An attribute value fromthe queue
        :rtype: Any
        """
        return self.queues[attribute_name].get(timeout=fetch_timeout)
