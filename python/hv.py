import mpod_control

#############################
#     Controller for HV 
#############################
hv_controller = mpod_control.mpod_control(
    module_type="LV", voltage_range="1000V", dry_run=True
)

hv_controller.set_output_voltage(
    "MODULE_1", channel="u200", voltage=180.0, current=0.001, rise_rate=5, fall_rate=10
)

hv_controller.set_output_voltage(
    "MODULE_2", channel="u201", voltage=180.0, current=0.001, rise_rate=5, fall_rate=10
)

hv_controller.set_output_voltage(
    "MODULE_3", channel="u202", voltage=180.0, current=0.001, rise_rate=5, fall_rate=10
)

hv_controller.set_output_voltage(
    "MODULE_4", channel="u203", voltage=180.0, current=0.001, rise_rate=5, fall_rate=10
)

# hv.controller.enable()
hv_controller.print_config()
