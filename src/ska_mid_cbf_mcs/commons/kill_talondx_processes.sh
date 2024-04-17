#!/bin/sh

# sh script for Talon-DX HPS that stops all SPFRx related device server processes

pid=$(ps alx | grep ska-mid-spfrx-controller-ds | grep -v grep | awk '{print $3}')
if [ $pid -gt 0 ]
then echo "Stopping SKA Mid SPFRx Controller Device Server pid=$pid ..."
     kill -9 $pid
else echo 'Unable to find SKA Mid SPFRx Controller Device Server process, skipping ...'
fi

pid=$(ps alx | grep ska-mid-spfrx-system | grep -v grep | awk '{print $3}')
if [ $pid -gt 0 ]
then echo "Stopping SKA Mid SPFRx Low Level Device Server pid=$pid ..."
     kill -9 $pid
else echo 'Unable to find SKA Mid SPFRx Low Level Device Server process, skipping ...'
fi

pid=$(ps alx | grep ska-talondx-temperature-monitor-ds | grep -v grep | awk '{print $3}')
if [ $pid -gt 0 ]
then echo "Stopping SKA Mid Talon-DX FPGA Temperature Monitor Device Server pid=$pid ..."
     kill -9 $pid
else echo 'Unable to find SKA Mid Talon-DX FPGA Temperature Monitor Device Server process, skipping ...'
fi

pid=$(ps alx | grep ska-talondx-bsp-ds | grep -v grep | awk '{print $3}')
if [ $pid -gt 0 ]
then echo "Stopping SKA Mid Talon-DX Board Support Package Device Server pid=$pid ..."
     kill -9 $pid
else echo 'Unable to find SKA Mid Talon-DX Board Support Package Device Server process, skipping ...'
fi