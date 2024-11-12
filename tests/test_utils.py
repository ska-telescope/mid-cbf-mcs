import tango
from assertpy import assert_that
from ska_control_model import AdminMode, SimulationMode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer

# Event Tracer's timeout in seconds
EVENT_TIMEOUT = 60


def device_online_and_on(
    device_under_test: context.DeviceProxy,
    event_tracer: TangoEventTracer,
) -> bool:
    """
    Helper function to start up and turn on the DUT.
    On is assumed to be a FastCommand.

    :param device_under_test: A fixture that provides a
        :py:class:`CbfDeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
    :param event_tracer: A :py:class:`TangoEventTracer` used to recieve subscribed change events from the device under test.
    """
    # Set a given device to AdminMode.ONLINE and DevState.ON
    device_under_test.simulationMode = SimulationMode.FALSE
    device_under_test.adminMode = AdminMode.ONLINE

    assert_that(event_tracer).within_timeout(
        EVENT_TIMEOUT
    ).has_change_event_occurred(
        device_name=device_under_test,
        attribute_name="adminMode",
        attribute_value=AdminMode.ONLINE,
    )

    assert_that(event_tracer).within_timeout(
        EVENT_TIMEOUT
    ).has_change_event_occurred(
        device_name=device_under_test,
        attribute_name="state",
        attribute_value=tango.DevState.OFF,
    )

    device_under_test.On()
    assert_that(event_tracer).within_timeout(
        EVENT_TIMEOUT
    ).has_change_event_occurred(
        device_name=device_under_test,
        attribute_name="state",
        attribute_value=tango.DevState.ON,
    )

    return device_under_test.adminMode == AdminMode.ONLINE
