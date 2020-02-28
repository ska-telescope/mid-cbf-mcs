"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

from PyTango.server import run
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
pkg_path = os.path.abspath(os.path.join(file_path, "../"))
sys.path.insert(0, pkg_path)

from CbfSubarray.CbfSubarray import CbfSubarray
from SearchWindow.SearchWindow import SearchWindow
from CbfSubarrayPssConfig.CbfSubarrayPssConfig import CbfSubarrayPssConfig
from SendConfig.SendConfig import SendConfig

def main(args=None, **kwargs):
    return run(classes=(SearchWindow, CbfSubarrayPssConfig, CbfSubarray, SendConfig), args=args, **kwargs)


if __name__ == '__main__':
    main()
