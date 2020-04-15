"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

from tango.server import run
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
pkg_path = os.path.abspath(os.path.join(file_path, "../"))
sys.path.insert(0, pkg_path)

from Fsp.Fsp import Fsp
from FspCorr.FspCorr import FspCorr
from FspPss.FspPss import FspPss
from FspPst.FspPst import FspPst
from FspVlbi.FspVlbi import FspVlbi
from FspCorrSubarray.FspCorrSubarray import FspCorrSubarray
from FspPssSubarray.FspPssSubarray import FspPssSubarray

def main(args=None, **kwargs):
    return run(
        classes=(FspCorr, FspPss, FspPst, FspVlbi, FspCorrSubarray, FspPssSubarray, Fsp),
        args=args, 
        **kwargs
    )


if __name__ == '__main__':
    main()
