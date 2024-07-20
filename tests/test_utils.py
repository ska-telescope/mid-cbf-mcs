import tango
from ska_control_model import AdminMode
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

EVENT_TIMEOUT = 10


def change_event_subscriber(
    dut: tango.DeviceProxy,
    change_event_attr_list: list,
    change_event_callbacks: MockTangoEventCallbackGroup,
) -> dict:
    # subscribe to and provide event IDs for all specified attributes
    attr_event_ids = {}
    for attr_name in change_event_attr_list:
        attr_event_ids[attr_name] = dut.subscribe_event(
            attr_name,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attr_name],
        )
        # assert against first empty change event received
        change_event_callbacks.assert_change_event(attr_name, Anything)
    return attr_event_ids


def device_online_and_on(dut: tango.DeviceProxy) -> bool:
    # set a given device to AdminMode.ONLINE and DevState.ON
    dut.adminMode = AdminMode.ONLINE
    dut.On()
    return (dut.adminMode == AdminMode.ONLINE) and (
        dut.state() == tango.DevState.ON
    )
