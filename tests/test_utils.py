from ska_control_model import AdminMode
import tango
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup


def change_event_subscriber(
    dut: tango.DeviceProxy,
    change_event_attr_list: list,
    change_event_callbacks: MockTangoEventCallbackGroup,
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

def device_online_and_on(dut: tango.DeviceProxy) -> bool:
    # set a given device to AdminMode.ONLINE and DevState.ON
    dut.adminMode = AdminMode.ONLINE
    dut.On()
    return (dut.adminMode == AdminMode.ONLINE) and (dut.state() == tango.DevState.ON)
