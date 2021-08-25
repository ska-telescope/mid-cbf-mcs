"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

from tango.server import run
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))

from ska_mid_cbf_mcs.fsp.fsp import Fsp
from ska_mid_cbf_mcs.fsp.corr import FspCorr
from ska_mid_cbf_mcs.fsp.pss import FspPss
from ska_mid_cbf_mcs.fsp.pst import FspPst
from ska_mid_cbf_mcs.fsp.vlbi import FspVlbi
from ska_mid_cbf_mcs.fsp.corr_subarray import FspCorrSubarray
from ska_mid_cbf_mcs.fsp.pss_subarray import FspPssSubarray
from ska_mid_cbf_mcs.fsp.pst_subarray import FspPstSubarray

__all__ = ["main"]

def main(args=None, **kwargs):
    return run(
        classes=(FspCorr, FspPss, FspPst, FspVlbi, FspCorrSubarray, FspPssSubarray, FspPstSubarray, Fsp),
        args=args, 
        **kwargs
    )


if __name__ == '__main__':
    main()
