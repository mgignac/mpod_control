import mpod_control

#############################
#     Controller for LV
#############################
lv_controller = mpod_control.mpod_control(
    module_type="LV", voltage_range="8V", dry_run=True
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
lv_controller.print_config()
