#!/bin/bash
#
# Script to stopt the CSP.LMC prototype TANGO devices.
# The script looks for the TANGO servers. If they are running it get their
# pids and send them a TERM signal.
#
# get the pid of the Csp prototype TANGO servers
server_running=$(ps -ef | grep '[p]ython csplmc' | awk '{print $9}')
# check if they are running and in case kill them
len=${#server_running}
if [ $len -gt 0 ]; then
    echo "Stopping the Csp prototype devices"	
    server_pid=$(ps -ef | grep '[p]ython csplmc' | awk '{print $2}')
    for t1 in $server_pid ;do
        kill -9 $t1
        if [ $? -eq 0 ]; then
		echo "Stopped server (PID $t1)"
        else 
	    echo "Failure in stopping the TANGO device servers"
        fi
    done
else 
    echo "No Csp prototype TANGO device running"	
fi

