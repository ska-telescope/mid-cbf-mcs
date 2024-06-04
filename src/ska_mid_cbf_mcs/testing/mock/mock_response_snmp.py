from __future__ import annotations

from typing import Any, List
from pysnmp import error as snmp_error


__all__ = ["MockGetResponseSNMP", "MockSetResponseSNMP"]

# This mock is currently purely imitating what the driver is asking for, not the real response object
def MockGetResponseSNMP(simulate_response_error: bool,
    sim_state: bool,) -> tuple: 

    if simulate_response_error:
        raise snmp_error.PySnmpError()

    returnObject: tuple = ()
    sim_state = 1 if sim_state else 2

    errorIndication = None
    errorStatus  = None
    errorIndex = None

    # First sim state has no meaning, just has to be an accessible value
    varBinds = [(sim_state, sim_state)]
    returnObject = (errorIndication, errorStatus, errorIndex, varBinds)
    
    return returnObject


def MockSetResponseSNMP(simulate_response_error: bool,
    sim_state: bool,) -> tuple: 
    
    if simulate_response_error:
        raise snmp_error.PySnmpError()

    returnObject: tuple = ()
    sim_state = 1 if sim_state else 2

    errorIndication = None
    errorStatus  = None
    errorIndex = None

    # First sim state has no meaning, just has to be an accessible value
    varBinds = [(sim_state, sim_state)]
    returnObject = (errorIndication, errorStatus, errorIndex, varBinds)
    
    return returnObject