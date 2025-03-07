# -*- coding: utf-8 -*-
#
# This file is part of the FspPstSubarray project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

import os

from tango.server import run

from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_device import FspCorrSubarray
from ska_mid_cbf_mcs.fsp.fsp_device import Fsp
from ska_mid_cbf_mcs.fsp.fsp_pst_subarray_device import FspPstSubarray

file_path = os.path.dirname(os.path.abspath(__file__))


__all__ = ["main"]


def main(args=None, **kwargs):
    return run(
        classes=(
            FspCorrSubarray,
            FspPstSubarray,
            Fsp,
        ),
        args=args,
        **kwargs
    )


if __name__ == "__main__":
    main()
