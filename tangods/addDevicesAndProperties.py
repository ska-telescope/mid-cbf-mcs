#!/usr/bin/env python
from tango import Database, DbDevInfo
from time import sleep
import json

timeSleep = 30
for x in range(10):
    try:
        # Connecting to the databaseds
        db = Database()
    except:
        # Could not connect to the databaseds. Retry after: str(timeSleep) seconds.
        print("Could not connect to database")
        sleep(timeSleep)

# Connected to the databaseds

# Update file path to devices.json in order to test locally
# To test on docker environment use path : /app/tangods/devices.json

with open('/app/tangods/devices.json', 'r') as file:
    jsonDevices = file.read()

# Loading devices.json file and creating an object
json_devices = json.loads(jsonDevices)

for device in json_devices:
    dev_info = DbDevInfo()
    dev_info._class = device["class"]
    dev_info.server = device["serverName"]
    dev_info.name = device["devName"]

    print("Adding {}...".format(device["devName"]))

    # Adding device
    db.add_device(dev_info)

    # Adding device properties
    for deviceProperty in device["deviceProperties"]:
        # Adding device property: deviceProperty["devPropValue"]
        # with value: deviceProperty["devPropValue"]
        if (deviceProperty["devPropName"]) != "" and (deviceProperty["devPropValue"] != ""):
            db.put_device_property(dev_info.name,
                                   {deviceProperty["devPropName"]:
                                        deviceProperty["devPropValue"]})

    """
    # Adding attribute properties
    for attributeProperty in device["attributeProperties"]:
        # Adding attribute property: attributeProperty["attrPropName"]
        # for attribute: attributeProperty["attributeName"]
        # with value: " + attributeProperty["attrPropValue"]
        if (attributeProperty["attrPropName"]) != "" and (attributeProperty["attrPropValue"] != ""):
            db.put_device_attribute_property(dev_info.name,
                                             {attributeProperty["attributeName"]:
                                                  {attributeProperty["attrPropName"]:
                                                       attributeProperty["attrPropValue"]}})
    """
