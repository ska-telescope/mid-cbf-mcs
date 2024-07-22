from __future__ import annotations

import json
from logging import Logger

from src.ska_mid_cbf_mcs.commons.global_enum import ScanConfiguration


class ScanConfigurationValidator:
    
    def __init__(
        self:  ScanConfigurationValidator,
        scan_configuration: str,
        logger: Logger,
    ) -> None:
        
        self.scan_configuration = scan_configuration
        self.logger = logger

    def validate_input(self: ScanConfigurationValidator) -> tuple[bool, str]:
        """
        Validates if the Scan Configuration in self.scan_configuration is valid

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """
        try:
            full_configuration = json.loads(self.scan_configuration)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            self.logger.info(msg)
            return (False,msg)

        scan_configuration_version = (
            (full_configuration["interface"]).split("/")
        )[-1]

        if scan_configuration_version in ScanConfiguration.ADR99_VERSIONS:
            result_code, msg = self._validate_input_ADR99(full_configuration)
        elif scan_configuration_version in ScanConfiguration.PRE_ADR99_VERSIONS:
            result_code, msg = self._validate_input_ADR99(full_configuration)
        else:
            msg = f"Error: The version defined in the Scan Configuration is not supported by MCS: version {scan_configuration_version}"
            result_code = False
        
        self.logger.info(msg)
        return (result_code,msg)



    def _validate_input_pre_ADR99(
        self: ScanConfigurationValidator, full_configuration: dict
    )-> tuple[bool, str]:
        """
        Validates if the Scan Configuration in self.scan_configuration is valid with the 4.0 version as defined in ADR 99

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """
        
        return (True, "Placeholder Return")

    def _validate_input_ADR99(
        self: ScanConfigurationValidator, full_configuration: dict
    )-> tuple[bool, str]:
        """
        Validates if the Scan Configuration in self.scan_configuration is valid before changes decided in ADR 99 

        :return: tuple with:
                    bool to indicate if the scan configuration is valid or not
                    str message about the configuration
        :rtype: tuple[bool, str]

        """
        return (True, "Placeholder Return")
