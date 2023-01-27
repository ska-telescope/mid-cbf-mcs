"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

import os

from tango.server import run

from ska_mid_cbf_mcs.fsp.fsp_corr_subarray import FspCorrSubarray
from ska_mid_cbf_mcs.fsp.fsp_device import Fsp
from ska_mid_cbf_mcs.fsp.fsp_hps_fsp_corr_controller_simulator import (
    HpsFspCorrControllerSimulator,
)
from ska_mid_cbf_mcs.fsp.fsp_pss import FspPss
from ska_mid_cbf_mcs.fsp.fsp_pss_subarray import FspPssSubarray
from ska_mid_cbf_mcs.fsp.fsp_pst import FspPst
from ska_mid_cbf_mcs.fsp.fsp_pst_subarray import FspPstSubarray
from ska_mid_cbf_mcs.fsp.fsp_vlbi import FspVlbi

file_path = os.path.dirname(os.path.abspath(__file__))


__all__ = ["main"]


def main(args=None, **kwargs):
    return run(
        classes=(
            HpsFspCorrControllerSimulator,
            FspPss,
            FspPst,
            FspVlbi,
            FspCorrSubarray,
            FspPssSubarray,
            FspPstSubarray,
            Fsp,
        ),
        args=args,
        **kwargs
    )


if __name__ == "__main__":
    main()
