import mpod_control

#############################
#     Controller for LV
#############################

lv_controller = mpod_control.mpod_control(
    module_type="LV", voltage_range="8V"
)

lv_controller.set_output_voltage_sense(
    "DIG_VIN", channel="u0", voltage=5.3, current=2.0, sense_rails=[4.6,5.5] 
)

lv_controller.set_output_voltage_sense(
    "ANA_POS_VIN", channel="u1", voltage=5.95, current=2.0, sense_rails=[5.0,6.2]
)

lv_controller.set_output_voltage_sense(
    "ANA_NEG_VIN", channel="u2", voltage=5.7, current=2.0, sense_rails=[5.0,6.0]
)

lv_controller.set_output_voltage_sense(
    "HY_VIN_A", channel="u3", voltage=5.2, current=2.0, sense_rails=[5.0,6.0]
)

lv_controller.print_config()
lv_controller.enable()
