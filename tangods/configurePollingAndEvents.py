#!/usr/bin/env python
from tango import Database, AttributeProxy, ChangeEventInfo, AttributeInfoEx, DevFailed, PeriodicEventInfo
import json
import time

timeSleep = 30
for x in range(10):
    try:
        # Connecting to the databaseds
        db = Database()
    except:
        # Could not connect to the databaseds. Retry after: str(timeSleep) seconds.
        print("Could not connect to database")
        time.sleep(timeSleep)

# Update file path to devices.json in order to test locally
# To test on docker environment use path : /app/tangods/devices.json

with open('/app/tangods/devices.json', 'r') as file:
    jsonDevices = file.read()

# Loading devices.json file and creating an object
json_devices = json.loads(jsonDevices)

# For some reason, this error is occurring:
# Failed to connect to device mid_csp_cbf/sub_elt/master
# The connection request was delayed.
# The last connection request was done less than 1000 ms ago

for device in json_devices:
    deviceName = device["devName"]
    dev_list = []

    if '*' == deviceName:
        # if we see a wildcard, do a search (haven't allowed for partial wildcard matching in devName)
        # I haven't allowed for class to be a wildcard, not sure if that's useful?
        search_class = device["class"]
        # if no server specified, search all
        all_instances = "{}/*".format(search_class)
        search_server = all_instances if "serverName" not in device else device["serverName"]
        servers = db.get_server_list(search_server)

        for server in servers:
            device_class_list = db.get_device_class_list(server)
            # make list into device/class pairs
            for dev, cls in zip(*[iter(device_class_list)]*2):
                if search_class == cls:
                    dev_list.append(dev)
    else:
        dev_list = [deviceName]

    # for each device instance, apply the attributeProperties from the JSON file
    for deviceName in dev_list:
        try:
            if "attributeProperties" in device:
                for attributeProperty in device["attributeProperties"]:
                    attributeProxy = AttributeProxy(deviceName + "/" + attributeProperty["attributeName"])
                    print("Device: ", deviceName, " Attribute: ", attributeProperty["attributeName"])
                    print("Polling Period: ", attributeProperty["pollingPeriod"])
                    if (attributeProperty["pollingPeriod"] != ""):
                        attributeProxy.poll(attributeProperty["pollingPeriod"])
                    else:
                        print("Skip setting polling period...")
                    if (attributeProperty["changeEventAbs"] != ""):
                        attrInfoEx = attributeProxy.get_config()
                        absChange = ChangeEventInfo()
                        absChange.abs_change = attributeProperty["changeEventAbs"]
                        attrInfoEx.events.ch_event = absChange
                        attributeProxy.set_config(attrInfoEx)
                    else:
                        print("Skip setting change event absolute...")
        except Exception as e:
            print(str(e))
            continue

