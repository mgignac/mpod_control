import os


class mpod_control:
    """
    Template class for controlling Wiener MPOD power supply system.
    Configurable parameters are based on MPOD documentation for LV and HV modules.
    Focus on output voltage, current limits, ramping speeds, and supervision thresholds.
    This is a template; integrate with actual hardware interface (e.g., SNMP or MUSEcontrol API).
    """

    # Default module type and ranges (configurable in __init__)
    DEFAULT_MODULE_TYPE = "LV"  # 'LV' or 'HV'
    LV_VOLTAGE_RANGES = {
        "8V": {"min": 0.0, "max": 8.0, "max_current": 10.0},
        "15V": {"min": 0.0, "max": 15.0, "max_current": 5.0},
        "30V": {"min": 0.0, "max": 30.0, "max_current": 2.5},
        "60V": {"min": 0.0, "max": 60.0, "max_current": 1.0},
        "120V": {"min": 0.0, "max": 120.0, "max_current": 0.1},
    }
    HV_VOLTAGE_RANGES = {
        "500V": {
            "min": 0.0,
            "max": 500.0,
            "max_current": 10.0,
        },  # Example; adjust per ISEG model
        "2kV": {"min": 0.0, "max": 2000.0, "max_current": 5.0},
        # Add more as needed, e.g., up to 10kV
    }
    DEFAULT_RAMP_RATE = 10.0  # V/s (1 to 500 for LV, lower for HV)
    DEFAULT_CURRENT_RAMP_RATE = 1.0  # A/s

    def __init__(
        self,
        ip_address_crate,
        module_type=DEFAULT_MODULE_TYPE,
        voltage_range="30V",
        max_current=None,
        ramp_up=DEFAULT_RAMP_RATE,
        ramp_down=DEFAULT_RAMP_RATE,
        supervision_max_current=None,
        supervision_max_power=50.0,
        supervision_max_temp=60.0,
        channel_id=0,
        crate_ip=None,
    ):
        """
        Default initializer for MPOD control.

        Args:
            module_type (str): 'LV' or 'HV' (default: 'LV').
            voltage_range (str): Key for voltage range, e.g., '30V' for LV_30V (default: '30V').
            max_current (float): Maximum current limit in A (default: from range).
            ramp_up (float): Voltage ramp-up rate in V/s (default: 10.0).
            ramp_down (float): Voltage ramp-down rate in V/s (default: 10.0).
            supervision_max_current (float): Max current supervision threshold in A (default: max_current).
            supervision_max_power (float): Max power supervision in W (default: 50.0).
            supervision_max_temp (float): Max temperature threshold in °C (default: 60.0).
            channel_id (int): Channel ID (0-based, default: 0).
            crate_ip (str): IP address for Ethernet control (optional).

        Raises:
            ValueError: If invalid module_type or voltage_range.
        """
        self.module_type = module_type
        self.voltage_range_key = voltage_range
        self.channel_id = channel_id
        self.crate_ip = crate_ip

        # Select range config
        if module_type == "LV":
            if voltage_range not in self.LV_VOLTAGE_RANGES:
                raise ValueError(
                    f"Invalid LV voltage range: {voltage_range}. Options: {list(self.LV_VOLTAGE_RANGES.keys())}"
                )
            self.range_config = self.LV_VOLTAGE_RANGES[voltage_range]
        elif module_type == "HV":
            if voltage_range not in self.HV_VOLTAGE_RANGES:
                raise ValueError(
                    f"Invalid HV voltage range: {voltage_range}. Options: {list(self.HV_VOLTAGE_RANGES.keys())}"
                )
            self.range_config = self.HV_VOLTAGE_RANGES[voltage_range]
        else:
            raise ValueError("module_type must be 'LV' or 'HV'")

        self.ip_address_crate = ip_address_crate

        # Configurable variables
        self.min_voltage = self.range_config["min"]
        self.max_voltage = self.range_config["max"]

        self.channel_names = {}
        self.output_voltages = {}
        self.output_currents = {}
        self.ramp_up_rates = {}  # V/s
        self.ramp_down_rates = {}  # V/s

        self.current_limit = (
            max_current or self.range_config["max_current"]
        )  # Current limit

        # Status
        self.is_on = False
        self.current_sense_voltage = 0.0  # Measured sense voltage (placeholder)
        self.current_terminal_voltage = 0.0  # Measured terminal voltage
        self.current_output_current = 0.0  # Measured current

    def snmpwalk_cmd(self):

        # TODO: conditionals paths/ip, etc
        cmd = "snmpwalk -v 2c "
        cmd += (
            "-M /sdf/home/m/mgignac/LDMX/MPOD/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB "
        )
        cmd += f"-c public {self.ip_address_crate} "
        return cmd

    def snmpget_cmd(self, user_cmd):

        # TODO: conditionals paths/ip, etc
        cmd = "snmpget -v 2c "
        cmd += (
            "-M /sdf/home/m/mgignac/LDMX/MPOD/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB "
        )
        cmd += f"-c public {self.ip_address_crate} "
        cmd += f"{user_cmd}"

        print(cmd)
        os.system(cmd)

        return cmd

    def snmpset_cmd(self, user_cmd):

        # TODO: conditionals paths/ip, etc
        cmd = "snmpset -v 2c "
        cmd += (
            "-M /sdf/home/m/mgignac/LDMX/MPOD/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB "
        )
        cmd += f"-c guru {self.ip_address_crate} "
        cmd += f"{user_cmd}"

        print(cmd)
        os.system(cmd)

        return cmd

    def print_outputNames(self):

        cmd = f"{self.snmpwalk_cmd()} outputName"
        print(cmd)
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

        if voltage < self.min_voltage or voltage > self.max_voltage:
            print(
                f"Error: Voltage {voltage}V out of range [{self.min_voltage}, {self.max_voltage}]V"
            )
            return False

        self.channel_names[channel] = name
        self.output_voltages[channel] = voltage
        self.output_currents[channel] = current
        self.ramp_up_rates[channel] = rise_rate
        self.ramp_down_rates[channel] = fall_rate

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
        print(f"  Channel ID:           {self.channel_id}")
        print(f"  Crate IP:             {self.crate_ip or 'Not set'}")

        print("\n[Voltage Limits]")
        print(f"  Min Voltage:          {self.min_voltage:>6.1f} V")
        print(f"  Max Voltage:          {self.max_voltage:>6.1f} V")

        print(f"  Channel voltages: ")
        for chan in self.output_voltages:
            print(f"      Channel {chan}:  {self.output_voltages[chan]} V")

        print("\n[Current Limits]")
        print(f"  Max Current:          {self.current_limit:>6.2f} A")

        print("\n[Ramp Rates]")
        print(f"  Voltage Ramp Up:      {self.ramp_up_rate:>6.1f} V/s")
        print(f"  Voltage Ramp Down:    {self.ramp_down_rate:>6.1f} V/s")

        print("\n[Supervision Thresholds]")
        print(f"  Min Sense Voltage:    {self.supervision_min_voltage:>6.1f} V")
        print(f"  Max Sense Voltage:    {self.supervision_max_voltage:>6.1f} V")
        print(
            f"  Max Terminal Voltage: {self.supervision_max_terminal_voltage:>6.1f} V"
        )
        print(f"  Max Current:          {self.supervision_max_current:>6.2f} A")
        print(f"  Max Power:            {self.supervision_max_power:>6.1f} W")
        print(f"  Max Temperature:      {self.supervision_max_temp:>6.1f} °C")

        print("\n[Current Status]")
        print(f"  Power On:             {'Yes' if self.is_on else 'No'}")
        print(f"  Sense Voltage:        {self.current_sense_voltage:>6.1f} V")
        print(f"  Terminal Voltage:     {self.current_terminal_voltage:>6.1f} V")
        print(f"  Output Current:       {self.current_output_current:>6.2f} A")

        print("\n" + "=" * 60)


#############################
#     Controller for LV
#############################
lv_controller = mpod_control(
    ip_address_crate="192.168.10.50", module_type="LV", voltage_range="8V", ramp_up=0.2
)

lv_controller.set_output_voltage(
    "DIG_VIN", channel="u0", voltage=5.5, current=2.0, rise_rate=0.1, fall_rate=0.1
)

lv_controller.set_output_voltage(
    "ANA_POS_VIN", channel="u1", voltage=5.5, current=2.0, rise_rate=0.1, fall_rate=0.1
)

lv_controller.set_output_voltage(
    "ANA_NEG_VIN", channel="u1", voltage=5.5, current=2.0, rise_rate=0.1, fall_rate=0.1
)

lv_controller.set_output_voltage(
    "HY_VIN_A", channel="u1", voltage=5.5, current=2.0, rise_rate=0.1, fall_rate=0.1
)

# lv.controller.enable()
# lv_controller.print_config()
