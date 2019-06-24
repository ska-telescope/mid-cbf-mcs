import json

with open('./devices.json', 'r') as file:
    jsonDevices = file.read()

json_devices = json.loads(jsonDevices)
