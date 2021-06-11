"""
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2021 National Research Council of Canada
"""

from tango.server import run
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
pkg_path = os.path.abspath(os.path.join(file_path, "../"))
sys.path.insert(0, pkg_path)

from CbfSubarray.CbfSubarray import CbfSubarray

from SendConfig.SendConfig import SendConfig

def main(args=None, **kwargs):
    # TODO: SendConfig looks like is a client driver for 
    # CbfSubarray.ConfigureScan(), therefore not needed; confirm that it 
    # can be removed. Notice though that running with the format below 
    # (run classes(c1, c2, ...)) does not work if only one class
    # is specified in the classes tuple, so keep SendConfig for now then,
    # possibly remove CbfSubarrayMulti alltogether.
    # return run(classes=(CbfSubarray), args=args, **kwargs)

    return run(classes=(CbfSubarray, SendConfig), args=args, **kwargs)

if __name__ == '__main__':
    main()
