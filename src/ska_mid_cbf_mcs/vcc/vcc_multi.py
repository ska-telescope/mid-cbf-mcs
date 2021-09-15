"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

from tango.server import run
import os
import sys

from ska_mid_cbf_mcs.vcc.vcc_device import Vcc
from ska_mid_cbf_mcs.vcc.vcc_band_1_and_2 import VccBand1And2
from ska_mid_cbf_mcs.vcc.vcc_band_3 import VccBand3
from ska_mid_cbf_mcs.vcc.vcc_band_4 import VccBand4
from ska_mid_cbf_mcs.vcc.vcc_band_5 import VccBand5
from ska_mid_cbf_mcs.vcc.vcc_search_window import VccSearchWindow

__all__ = ["main"]

def main(args=None, **kwargs):
    return run(
        classes=(VccBand1And2, VccBand3, VccBand4, VccBand5, VccSearchWindow, Vcc), 
        args=args, 
        **kwargs
    )


if __name__ == '__main__':
    main()
