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


def trim_snmpget_output(out):
    """Trim the output of an snmpget call to just the value at the end

    The (rough) spec looks like

        NAME-SPACE::parameter.mpod_name = [Opaque: ] type: val [units]

    - NAME-SPACE appears to always be WIENER-CRATE-MIB (makes sense for us)
    - 'Opaque: ' is only included for read-only parameters
    - 'type' is either 'INTEGER' or 'Float'

    In any case, I just get the last segment of text after splitting by 
    the colon ':' which provides the val and maybe its units.
    """

    return out.split(':')[-1].strip()


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
        """run a net-snmp program using the configured install

        Parameters
        ----------
        cmd: str
            one of the snmp programs (e.g. 'get' for snmpget)
        args: List[str]
            further arguments to the program

        If we are configured to be a dry run, we just print
        the constructed command and then return 'did not run'.
        Otherwise, we run the command with subprocess.run,
        capture the output assuming its text, check that
        the exit code is zero and return the stdout of
        the command.
        """

        permissions = 'public'
        if cmd == 'set':
            permissions = 'guru'
        cmd = [
            f'{self.net_snmp_install}/bin/snmp{cmd}',
            '-v', '2c',
        ]
        if self.mibs_dir is not None:
            cmd += ['-M', self.mibs_dir]
        cmd += ['-m', '+WIENER-CRATE-MIB']
        cmd += ['-c', permissions]
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
        """run a snmpwalk call

        Parameters
        ----------
        args: List[str]
            arguments to provide to snmpwalk
        """

        return self._snmp_cmd('walk', *args)


    def snmpget_cmd(self, *args, raw = False):
        """run an snmpget call

        Parameters
        ----------
        args: List[str]
            arguments to provide to snmpget
        raw: bool
            whether to post-process output
            The post-processing attempts to trim redundant information and
            just get the specific values.
            See the trim_snmpget_output for details
        """

        stdout = self._snmp_cmd('get', *args)
        if raw:
            return stdout
        return trim_snmpget_output(stdout)


    def snmpset_cmd(self, *args):
        """run a snmpset call

        Parameters
        ----------
        args: List[str]
            arguments to provide to snmpset
        """

        return self._snmp_cmd('set', *args)


    def print_outputNames(self):
        return self.snmpwalk_cmd('outputName')


    @command
    def print_crate_properties(self, raw = False):
        """print the properties of the MPOD housing crate

        Parameters
        ----------
        raw: bool
            whether to post-process the output of the snmpget
        """

        crate_properties = {
            name: self.snmpget_cmd(name, raw = raw)
            for name in [
                #"psFirmwareVersion", # not in MIB spec
                "psSerialNumber",
                "fanAirTemperature",
                "fanNominalSpeed",
                "fanNumberOfFans",
                "fanSpeed",
            ]
        }
        print(json.dumps(crate_properties, indent=2))


    @command
    def status(self, channel = None, raw = False, echo = True):
        """retrieve the status of the current configuration

        Parameters
        ----------
        channel: str
            our name of specific channel to focus on
        raw: bool
            whether to post-process output from snmpget commands
            The post-processing attempts to trim redundant information and
            just get the specific values.
        echo: bool
            whether to print the status before returning it
        """

        channels = self.channels
        if channel is not None:
            channels = { channel:  self.channels[channel] }

        status = {
            name: {
                param: self.snmpget_cmd(f'{param}.{channel.mpod_name}', raw = raw)
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
    def configure(self, uchan = None):
        """apply the current configuration to the MPOD

        Parameters
        ----------
        uchan: str
            mpod channel name to enable (and only this one)
            if None, enable all of the channels in the loaded configuration in order
        """
        for name, channel in self.channels.items():
            if uchan is not None and channel.mpod_name != uchan:
                continue
            print(f'configuring {name}')

            if channel.sense_rails is not None:
                self.snmpset_cmd(f"outputSupervisionMinSenseVoltage.{channel.mpod_name}", "F",  str(channel.sense_rails[0]))
                self.snmpset_cmd(f"outputSupervisionMaxSenseVoltage.{channel.mpod_name}", "F", str(channel.sense_rails[1]))

            self.snmpset_cmd(f"outputVoltage.{channel.mpod_name}", "F", str(channel.voltage))
            self.snmpset_cmd(f"outputCurrent.{channel.mpod_name}", "F", str(channel.current))

            if channel.rise_rate is not None and channel.rise_rate > 0:
                self.snmpset_cmd(f"outputVoltageRiseRate.{channel.mpod_name}", "F", str(channel.rise_rate))
            if channel.fall_rate is not None and channel.fall_rate > 0:
                self.snmpset_cmd(f"outputVoltageFallRate.{channel.mpod_name}", "F", str(channel.fall_rate))

            self.status(name)
         

    @command
    def enable(self, uchan = None):
        """enable the current configuration

        Parameters
        ----------
        uchan: str
            mpod channel name to enable (and only this one)
            if None, enable all of the channels in the loaded configuration in order
        """
        self.configure(uchan)

        for name, channel in self.channels.items():
            if uchan is not None and channel.mpod_name != uchan:
                continue

            print(f'enabling {name}')
            self.snmpset_cmd(f'outputSwitch.{channel.mpod_name}', 'i', '1')
            

    @command
    def disable(self, uchan = None):
        """disable the current channels

        Parameters
        ----------
        uchan: str
            mpod channel name to disable (and only this one)
            if None, disable all of the channels in the loaded configuration in reverse order
        """

        for name, channel in reversed(self.channels.items()):
            if uchan is not None and channel.mpod_name != uchan:
                continue
            print(f'disabling {name}')
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

    try:
        mc = mpod_control.from_json(args.config, dry_run = args.dry_run)
        getattr(mc, args.command)()
    except subprocess.CalledProcessError as e:
        print(f'Called process returned non-zero exit status {e.returncode}')
        print('cmd:', *e.cmd)
        print('stderr:\n', e.stderr.strip())
        if e.stdout.strip() != '':
            print('stdout:\n', e.stdout.strip())


if __name__ == '__main__':
    main()
