
if [ "$#" -ne 1 ]; then
	    echo "Usage:   ./hps_master_run <server_instance>"
	        exit 1
fi

export TANGO_HOST=<hostname>:<port>

SERVER_INST="$1"

/lib/firmware/hps_software/./dshpsmaster ${SERVER_INST} -v4 &
sleep 1s

# Note: When finished, to find and kill the processes started by this script:
# pkill -f <server_instance>