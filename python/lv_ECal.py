import mpod_control

#############################
#     Controller for LV
#############################

lv_controller = mpod_control.mpod_control(
    module_type="LV_ECal", voltage_range="8V"
)

lv_controller.set_output_voltage_sense(
    "ECal_Ch0", channel="u104", voltage=7.5, current=2.0, sense_rails=[7.0,8.0] 
)

lv_controller.set_output_voltage_sense(
    "ECal_Ch1", channel="u105", voltage=7.5, current=2.0, sense_rails=[7.0,8.0]
)

lv_controller.set_output_voltage_sense(
    "ECal_Ch2", channel="u106", voltage=7.5, current=2.0, sense_rails=[7.0,8.0]
)

lv_controller.print_config()
lv_controller.enable()
