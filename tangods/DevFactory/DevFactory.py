import logging
import tango

__all__ = ["DevFactory"]

class DevFactory:
    """
    Ported from ska_tango_base; 
    https://gitlab.com/ska-telescope/ska-tango-examples/-/blob/master/src/ska_tango_examples/DevFactory.py
    
    Following descriptions copied from above:

    "This class is an easy attempt to develop the concept developed by MCCS team
    in the following confluence page:
    https://confluence.skatelescope.org/display/SE/Running+BDD+tests+in+multiple+harnesses

    It is a factory class which provide the ability to create an object of
    type DeviceProxy.

    When testing the static variable _test_context is an instance of
    the TANGO class MultiDeviceTestContext.

    More information on tango testing can be found at the following link:
    https://pytango.readthedocs.io/en/stable/testing.html"

    """

    _test_context = None

    def __init__(self, green_mode=tango.GreenMode.Synchronous):
        self.device_proxys = {}
        self.logger = logging.getLogger(__name__)
        self.default_green_mode = green_mode
    
    def get_device(self, device_name, green_mode=None):
        """
        Create (if not done before) a DeviceProxy for the Device fqdn

        :param dev_name: Device name
        :param green_mode: tango.GreenMode (synchronous by default)

        :return: DeviceProxy
        """
        if green_mode is None:
            green_mode = self.default_green_mode

        if DevFactory._test_context is None:
            if device_name not in self.device_proxys:
                self.logger.info("Creating Proxy for %s", device_name)
                self.device_proxys[device_name] = tango.DeviceProxy(
                    device_name, green_mode=green_mode
                )
            return self.device_proxys[device_name]
        else:
            return DevFactory._test_context.get_device(device_name)
