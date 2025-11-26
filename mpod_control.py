import os
import subprocess
import typing
import json
from dataclasses import dataclass
from pathlib import Path

def command(func):
    """decorator to itemize members that are CLI commands"""
    command.__list__.append(func.__name__)
    return func
command.__list__ = []


@dataclass
class _channel:
    """A single channel output from MPOD

    mpod_name: str
        name of channel as identified by MPOD
    voltage: float
        output voltage setting for MPOD
    current: float
        limiting output current for MPOD
    rise_rate: float
        how quickly to ramp up to the set voltage in V/s
    fall_rate: float
        how quickly to ramp down from the set voltage in V/s
    sense_rails: tuple(float)
        voltage lower and upper bounds
    """
    mpod_name: str
    voltage: float
    current: float
    rise_rate: float = -1
    fall_rate: float = 1
    sense_rails: typing.Tuple[float,float] = ()


class mpod_control:
    """
    Class for controlling Wiener MPOD power supply system.
    """

    def __init__(self, dry_run = False):
        self.ip_address_crate = os.environ.get("MPOD_CRATE_IP", '192.168.10.50')
        self.net_snmp_install = os.environ.get('NET_SNMP_INSTALL', '/u1/ldmx/net-snmp-5.9.4/install')
        self.mibs_dir = os.environ.get('NET_SNMP_MIBS_DIR', None)

        self.module_type      = None
        self.dry_run          = dry_run
        self.voltage_range    = None
        self.channels = {}


    @classmethod
    def from_json(cls, filepath, **kwargs):
        with open(filepath, 'r') as f:
            config = json.load(f)

        obj = cls(**kwargs)
        obj.module_type = config["module_type"]
        obj.voltage_range = config["voltage_range"]
        for name, chan in config["channels"].items():
            obj.channels[name] = _channel(
                mpod_name = chan["mpod_name"],
                voltage = chan["voltage"],
                current = chan["current"],
                sense_rails = chan.get("sense_rails", None),
                rise_rate = chan.get("rise_rate", None),
                fall_rate = chan.get("fall_rate", None),
            )

        return obj


    def _snmp_cmd(self, cmd, *args):
        cmd = [
            f'{self.net_snmp_install}/bin/snmp{cmd}',
            '-v', '2c',
        ]
        if self.mibs_dir is not None:
            cmd += ['-M', self.mibs_dir]
        cmd += ['-m', '+WIENER-CRATE-MIB']
        cmd += ['-c', 'public' if cmd != 'set' else 'guru']
        cmd += [self.ip_address_crate]
        cmd += args
        if self.dry_run:
            print(cmd)
            return 'did not run'
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
            result.check_returncode()
            return result.stdout.strip()


    def snmpwalk_cmd(self, *args):
        return self._snmp_cmd('walk')


    def snmpget_cmd(self, *args):
        return self._snmp_cmd('get', *args)


    def snmpset_cmd(self, *args):
        return self._snmp_cmd('set', *args)


    def print_outputNames(self):
        return self.snmpwalk_cmd('outputName')


    def print_crate_properties(self):
        crate_properties = [
            "psFirmwareVersion",
            "psSerialNumber",
            "fanAirTemperature",
            "fanNominalSpeed",
            "fanNumberOfFans",
            "fanSpeed",
        ]

        for crate_param in crate_properties:
            print(self.snmpget_cmd(crate_param))


    @command
    def status(self, channel = None):
        channels = self.channels
        if channel is not None:
            channels = { channel:  self.channels[channel] }

        status = {
            name: {
                param: self.snmpget_cmd(f'{param}.{channel.mpod_name}')
                for param in [
                    "outputSwitch",
                    "outputVoltage",
                    "outputCurrent",
                    "outputSupervisionMinSenseVoltage",
                    "outputSupervisionMaxSenseVoltage",
                    "outputVoltageRiseRate",
                    "outputVoltageFallRate",
                    "outputMeasurementTerminalVoltage",
                    "outputMeasurementCurrent"
                ]
            }
            for name, channel in channels.items()
        }
        print(json.dumps(status, indent=2))
        return status
         

    @command
    def enable(self, uchan = None):
        for name, channel in self.channels.items():
            if uchan is not None and channel.mpod_name != uchan:
                continue
            print(name)

            if channel.sense_rails is not None:
                self.snmpset_cmd(f"outputSupervisionMinSenseVoltage.{channel.mpod_name} F {channel.sense_rails[0]}")
                self.snmpset_cmd(f"outputSupervisionMaxSenseVoltage.{channel.mpod_name} F {channel.sense_rails[1]}")

            self.snmpset_cmd(f"outputVoltage.{channel.mpod_name} F {channel.voltage}")
            self.snmpset_cmd(f"outputCurrent.{channel.mpod_name} F {channel.current}")

            if channel.rise_rate is not None and channel.rise_rate > 0:
                self.snmpset_cmd(f"outputVoltageRiseRate.{channel.mpod_name} F {channel.rise_rate}")
            if channel.fall_rate is not None and channel.fall_rate > 0:
                self.snmpset_cmd(f"outputVoltageFallRate.{channel.mpod_name} F {channel.fall_rate}")

            self.status(name)

            self.snmpset_cmd(f'outputSwitch.{channel.mpod_name} i 1')
            

    @command
    def disable(self, uchan = None):
        for name, channel in reversed(self.channels.items()):
            if uchan is not None and channel.mpod_name != uchan:
                continue
            print(name)
            self.snmpset_cmd(f"outputSwitch.{channel.mpod_name} i 0")


    @command
    def print(self):
        """
        Print the complete configuration and status with nice formatting.
        Uses formatted sections for readability.
        """
        print("=" * 60)
        print("MPOD Control Configuration Dump")
        print("=" * 60)

        print("\n[Module Information]")
        print(f"  Module Type:          {self.module_type}")
        print(f"  Voltage Range:        {self.voltage_range}")
        print(f"  Crate IP:             {self.ip_address_crate or 'Not set'}")

        print(f"  Channel information: ")
        for name, chan in self.channels.items():
            print(f"      Channel {name:16s}  {chan.mpod_name}")
            print(f"          > Output voltage:     {chan.voltage} V")
            print(f"          > Current compliance: {chan.current} A")

        print("\n" + "=" * 60)


def main(): 
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='just print commands we would try to run')
    parser.add_argument('command', choices=command.__list__, help='Command to run')
    parser.add_argument('config', help='JSON configuration for an MPOD connection')
    args = parser.parse_args()

    mc = mpod_control.from_json(args.config, dry_run = args.dry_run)
    getattr(mc, args.command)()


if __name__ == '__main__':
    main()
