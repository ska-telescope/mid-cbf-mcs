import tango
from assertpy import assert_that
from ska_control_model import AdminMode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

EVENT_TIMEOUT = 30


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


def device_online_and_on(
    dut: context.DeviceProxy,
    event_tracer: TangoEventTracer,
) -> bool:
    obs_devices = [
        "mid_csp_cbf/vcc",
        "mid_csp_cbf/sub_elt/subarray",
        "mid_csp_cbf/fspCorrSubarray",
    ]

    # set a given device to AdminMode.ONLINE and DevState.ON
    dut.adminMode = AdminMode.ONLINE
    assert_that(event_tracer).within_timeout(
        EVENT_TIMEOUT
    ).has_change_event_occurred(
        device_name=dut,
        attribute_name="state",
        attribute_value=tango.DevState.OFF,
    )

    dut.On()
    assert_that(event_tracer).within_timeout(
        EVENT_TIMEOUT
    ).has_change_event_occurred(
        device_name=dut,
        attribute_name="state",
        attribute_value=tango.DevState.ON,
    )

    # assert if any captured events have gone unaddressed
    # assert_that(event_tracer).within_timeout(
    #     EVENT_TIMEOUT
    # ).hasnt_change_event_occurred(
    #     device_name=dut,
    # )

    return dut.adminMode == AdminMode.ONLINE
