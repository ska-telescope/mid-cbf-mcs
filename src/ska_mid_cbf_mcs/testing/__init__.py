from assertpy import add_extension

from .cbf_assertions import (
    cbf_has_change_event_occurred,
    cbf_hasnt_change_event_occurred,
)
from ska_tango_testing.integration.tracer import TangoEventTracer

# register the tracer custom assertions
add_extension(cbf_has_change_event_occurred)
add_extension(cbf_hasnt_change_event_occurred)

# expose just a minimal set of classes and functions
__all__ = [
    "TangoEventTracer",
]
