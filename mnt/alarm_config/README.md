# Alarm Handler Configurations File

This directory contains the configuration file that is to be import to the Alarm Handler.

The files will tell the Alarm Handler:
- The attribute to monitor by the Alarm Handler
- The type of alarm (Warning, Alarm) to be thrown when conditions are met
- The conditions (values, the eqaulities) for the alarm
- The message for when the alarm condition is met
- The action that is to occur when the alarm condition is met

The following is a template of the format and values needed:

```
tag: <string> the name for the alarm:
  - attribute: <string> name of attribute to monitor
  - type: <Tango ATTR_QUALITY enum> (ATTR_ALARM,ATTR_WARNING)
  - value: <int | float | bool> the target value for the condition
  - value_greater: <bool> trigger alarm if the attribute's value 
                        is greater than (True) or less than (False) the value provided
  - value_equal: <bool> trigger alarm if the attribute's value 
                        is equal to (True) to the value provided
  - message: <string> string with quotes "example"
  - callback: <optional | function> name of callback function
```
