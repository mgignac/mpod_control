# MPOD Control

Simple class to control MPOD modules through SNMP commands

## Dependencies
Used and tested with [net-snmp](https://www.net-snmp.org/) v5.9.4.

## Usage
Besides access to the executables installed by `net-snmp`, we
avoid using any other Python libraries.
```
python mpod_control.py {enable|disable|print} {config.json}
```

- Need `WIENER-CRATE-MIB.txt` to specify how MPOD talks via SNMP
