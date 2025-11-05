import os
import env

class mpod_control:

    """
    Class for controlling Wiener MPOD power supply system.
    """

    def __init__(
        self,
        module_type="LV",
        voltage_range="8V",
        dry_run=False
    ):

        _env = env.load_dotenv()

        self.ip_address_crate = _env["CRATE_IP"]
        self.module_type      = module_type
        self.dry_run          = dry_run

        self.voltage_range_key = voltage_range

        self.channel_names    = {}
        self.output_voltages  = {}
        self.output_currents  = {}
        self.ramp_up_rates    = {}  # V/s
        self.ramp_down_rates  = {}  # V/s

        # Status
        self.is_on = False

    def snmpwalk_cmd(self):

        # TODO: conditionals paths/ip, etc
        cmd = "snmpwalk -v 2c "
        cmd += (
            "-M /sdf/home/m/mgignac/LDMX/MPOD/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB "
        )
        cmd += f"-c public {self.ip_address_crate} "

        if self.dry_run:
          print(cmd)
        else:
          os.system(cmd)


    def snmpget_cmd(self, user_cmd):

        # TODO: conditionals paths/ip, etc
        cmd = "snmpget -v 2c "
        cmd += (
            "-M /sdf/home/m/mgignac/LDMX/MPOD/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB "
        )
        cmd += f"-c public {self.ip_address_crate} "
        cmd += f"{user_cmd}"

        if self.dry_run:
          print(cmd)
        else:
          os.system(cmd)

    def snmpset_cmd(self, user_cmd):

        # TODO: conditionals paths/ip, etc
        cmd = "snmpset -v 2c "
        cmd += (
            "-M /sdf/home/m/mgignac/LDMX/MPOD/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB "
        )
        cmd += f"-c guru {self.ip_address_crate} "
        cmd += f"{user_cmd}"

        if self.dry_run:
          print(cmd)
        else:
          os.system(cmd)


    def print_outputNames(self):

        cmd = f"{self.snmpwalk_cmd()} outputName"
        if self.dry_run:
          print(cmd)
        else:
          os.system(cmd)


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
            self.snmpget_cmd(crate_param)

    def print_channel_status(self, channel):

        ch_params = [
            "outputSwitch",
            "outputVoltage",
            "outputCurrent",
            "outputVoltageRiseRate",
            "outputVoltageFallRate",
        ]

        for ch_param in ch_params:
            self.snmpget_cmd(f"{ch_param}.{channel}")

    def set_output_voltage(self, name, channel, voltage, current, rise_rate, fall_rate):

        self.channel_names[channel]    = name
        self.output_voltages[channel]  = voltage
        self.output_currents[channel]  = current
        self.ramp_up_rates[channel]    = rise_rate
        self.ramp_down_rates[channel]  = fall_rate

        # Output voltage
        print(f"**********************************************************")
        print(f"Setting output voltage to {voltage}V")
        self.snmpset_cmd(f"outputVoltage.{channel} F {voltage}")
        print(f"**********************************************************")

        # Current limit
        print(f"**********************************************************")
        print(f"Setting output current to {current}A")
        self.snmpset_cmd(f"outputCurrent.{channel} F {current}")
        print(f"**********************************************************")

        # Channel ramp rate
        print(f"Setting voltage rise and fall rate to {rise_rate} and {fall_rate} V/s")
        print(f"**********************************************************")
        self.snmpset_cmd(f"outputVoltageRiseRate.{channel} F {rise_rate}")
        self.snmpset_cmd(f"outputVoltageFallRate.{channel} F {fall_rate}")
        print(f"**********************************************************")

        # Print channel properties
        self.print_channel_status(channel)

        return True

    def print_config(self):
        """
        Print the complete configuration and status with nice formatting.
        Uses formatted sections for readability.
        """
        print("=" * 60)
        print("MPOD Control Configuration Dump")
        print("=" * 60)

        print("\n[Module Information]")
        print(f"  Module Type:          {self.module_type}")
        print(f"  Voltage Range:        {self.voltage_range_key}")
        print(f"  Crate IP:             {self.ip_address_crate or 'Not set'}")

        print(f"  Channel information: ")
        for chan in self.output_voltages:
            print(f"      Channel {chan}:  {self.channel_names[chan]}")
            print(f"          > Output voltage:     {self.output_voltages[chan]} V")
            print(f"          > Current compliance: {self.output_currents[chan]} A")

        print("\n" + "=" * 60)

