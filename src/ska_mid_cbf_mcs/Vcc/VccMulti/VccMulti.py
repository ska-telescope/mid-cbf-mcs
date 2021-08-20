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

from Vcc.Vcc import Vcc
from VccBand1And2.VccBand1And2 import VccBand1And2
from VccBand3.VccBand3 import VccBand3
from VccBand4.VccBand4 import VccBand4
from VccBand5.VccBand5 import VccBand5
from VccSearchWindow.VccSearchWindow import VccSearchWindow

def main(args=None, **kwargs):
    return run(
        classes=(VccBand1And2, VccBand3, VccBand4, VccBand5, VccSearchWindow, Vcc), 
        args=args, 
        **kwargs
    )


if __name__ == '__main__':
    main()
