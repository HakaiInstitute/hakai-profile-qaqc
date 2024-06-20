from pathlib import Path

CTD_CAST_VARIABLES = [
    "ctd_cast_pk",
    "organization",
    "hakai_id",
    "processing_stage",
    "process_error",
    "cruise",
    "vessel",
    "operators",
    "comments",
    "cast_type",
    "no_cast",
    "bottle_drop",
    "processing_software_version",
]

# Subset of variables to download from CTD_CAST_DATA_ENDPOINT
CTD_CAST_DATA_VARIABLES = [
    "ctd_file_pk",
    "ctd_cast_pk",
    "organization",
    "hakai_id",
    "ctd_data_pk",
    "filename",
    "device_model",
    "device_sn",
    "device_firmware",
    "sensors_submerged",
    "file_processing_stage",
    "work_area",
    "cruise",
    "station",
    "cast_number",
    "station_longitude",
    "station_latitude",
    "distance_from_station",
    "latitude",
    "longitude",
    "location_flag",
    "location_flag_level_1",
    "process_flag",
    "process_flag_level_1",
    "start_dt",
    "bottom_dt",
    "end_dt",
    "duration",
    "start_depth",
    "bottom_depth",
    "target_depth",
    "drop_speed",
    "vessel",
    "direction_flag",
    "measurement_dt",
    "descent_rate",
    "conductivity",
    "conductivity_flag",
    "conductivity_flag_level_1",
    "temperature",
    "temperature_flag",
    "temperature_flag_level_1",
    "depth",
    "depth_flag",
    "depth_flag_level_1",
    "pressure",
    "pressure_flag",
    "pressure_flag_level_1",
    "par",
    "par_flag",
    "par_flag_level_1",
    "flc",
    "flc_flag",
    "flc_flag_level_1",
    "turbidity",
    "turbidity_flag",
    "turbidity_flag_level_1",
    "ph",
    "ph_flag",
    "ph_flag_level_1",
    "salinity",
    "salinity_flag",
    "salinity_flag_level_1",
    "spec_cond",
    "spec_cond_flag",
    "spec_cond_flag_level_1",
    "dissolved_oxygen_ml_l",
    "dissolved_oxygen_ml_l_flag",
    "dissolved_oxygen_ml_l_flag_level_1",
    "rinko_do_ml_l",
    "rinko_do_ml_l_flag",
    "rinko_do_ml_l_flag_level_1",
    "dissolved_oxygen_percent",
    "dissolved_oxygen_percent_flag",
    "dissolved_oxygen_percent_flag_level_1",
    "oxygen_voltage",
    "oxygen_voltage_flag",
    "oxygen_voltage_flag_level_1",
    "c_star_at",
    "c_star_at_flag",
    "c_star_at_flag_level_1",
    "sos_un",
    "sos_un_flag",
    "sos_un_flag_level_1",
    "backscatter_beta",
    "backscatter_beta_flag",
    "backscatter_beta_flag_level_1",
    "cdom_ppb",
    "cdom_ppb_flag",
    "cdom_ppb_flag_level_1",
]


# Hakai ID Test suite liste
def load_test_suite() -> list[str]:
    test_suite_list = (
        (Path(__file__).parent / "config" / "HAKAI_ID_TEST_SUITE.txt")
        .read_text()
        .split("\n")
    )
    return [
        line.split("#")[0].strip()
        for line in test_suite_list
        if line and not line.strip().startswith("#")
    ]


HAKAI_TEST_SUITE = load_test_suite()
