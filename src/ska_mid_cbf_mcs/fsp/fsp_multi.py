"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

from tango.server import run
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))

from ska_mid_cbf_mcs.fsp.fsp_device import Fsp
from ska_mid_cbf_mcs.fsp.fsp_corr import FspCorr
from ska_mid_cbf_mcs.fsp.fsp_pss import FspPss
from ska_mid_cbf_mcs.fsp.fsp_pst import FspPst
from ska_mid_cbf_mcs.fsp.fsp_vlbi import FspVlbi
from ska_mid_cbf_mcs.fsp.fsp_corr_subarray import FspCorrSubarray
from ska_mid_cbf_mcs.fsp.fsp_pss_subarray import FspPssSubarray
from ska_mid_cbf_mcs.fsp.fsp_pst_subarray import FspPstSubarray

__all__ = ["main"]

def main(args=None, **kwargs):
    return run(
        classes=(FspCorr, FspPss, FspPst, FspVlbi, FspCorrSubarray, FspPssSubarray, FspPstSubarray, Fsp),
        args=args, 
        **kwargs
    )


if __name__ == '__main__':
    main()
