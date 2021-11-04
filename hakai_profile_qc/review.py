import pandas as pd

import re
from ioos_qc.qartod import qartod_compare, QartodFlags
from ioos_qc.config import Config
from ioos_qc.streams import PandasStream
from ioos_qc.stores import PandasStore

from hakai_profile_qc import hakai_tests, get, utils

import argparse
import warnings
import os
import json

from tqdm import tqdm

tqdm.pandas()


def run_ioosqc_on_dataframe(df, qc_config, tinp="t", zinp="z", lat="lat", lon="lon"):
    """
    Apply ioos_qc configuration to a Pandas DataFrame by using the PandasStream mand PandasStore methods from ioos_qc
    """
    # Reset index ioos_qc failed otherwise
    original_index = list(df.index.names)
    if original_index == [None]:
        original_index = ["index"]
    df = df.reset_index()

    # Set Stream
    stream = PandasStream(df, time=tinp, z=zinp, lat=lat, lon=lon)
    # Set Configuration
    c = Config(qc_config)
    # Run
    results = stream.run(c)
    # Save to a pandas DataFrame
    store = PandasStore(results, axes={"t": tinp, "z": zinp, "lat": lat, "lon": lon})
    result_store = store.save(write_data=False, write_axes=False)

    return df.join(result_store).set_index(original_index)


def tests_on_profiles(
    df,
    hakai_stations,
    qc_config,
    profile_id="hakai_id",
    direction_flag="direction_flag",
    tinp="measurement_dt",
    zinp="depth",
    lon="longitude",
    lat="latitude",
):
    """
    Main method that runs on a number of profiles a series of QARTOD tests and specific to the Hakai CTD Dataset.
    """
    # Regroup profiles by profile_id and direction and sort them along zinp
    df = df.sort_values(by=[profile_id, direction_flag, zinp])

    # Retrieve hakai tests parameters if provided in the config file
    if "hakai_tests" in qc_config:
        hakai_tests_config = qc_config.pop("hakai_tests")
        hakai_tests_config = hakai_tests_config.pop("hakai")
    else:
        hakai_tests_config = {}

    # Retrieve tested variables list
    tested_variable_list = []
    for context in qc_config["contexts"]:
        for stream, att in context["streams"].items():
            if stream not in tested_variable_list:
                tested_variable_list += [stream]

    # Find Flag values present in the data, attach a FAIL QARTOD Flag to them and replace them by NaN.
    #  Hakai database ingested some seabird flags -9.99E-29 which need to be recognized and removed.
    if "bad_value_test" in hakai_tests_config:
        print(f'Flag Bad Values: {hakai_tests_config["bad_value_test"]["flag_list"]}')
        df = hakai_tests.bad_value_test(
            df,
            variables=hakai_tests_config["bad_value_test"]["variables"],
            flag_list=hakai_tests_config["bad_value_test"]["flag_list"],
        )

    # Run QARTOD tests
    groupby = [profile_id, direction_flag]
    tqdm.pandas(desc=f"Apply QARTOD Tests to individual {groupby}", unit="profile")
    df = df.groupby(groupby, as_index=False).progress_apply(
        lambda x: run_ioosqc_on_dataframe(
            x, qc_config, tinp=tinp, zinp=zinp, lat=lat, lon=lon
        ),
    )
    df = df.reset_index(drop=True)

    # HAKAI SPECIFIC TESTS #
    # This section regroup different non QARTOD tests which are specific to Hakai profile dataset. Most of the them
    # uses the pandas dataframe to transform the data and apply divers tests.
    # DO CAP DETECTION
    if any(df["direction_flag"] == "u") and ("do_cap_test" in hakai_tests_config):
        for key in hakai_tests_config["do_cap_test"]["variable"]:
            print("DO Cap Detection to " + key + " variable")
            hakai_tests.do_cap_test(
                df,
                key,
                profile_id=profile_id,
                depth_var=zinp,
                direction_flag=direction_flag,
                bin_size=hakai_tests_config["do_cap_test"]["bin_size"],
                suspect_threshold=hakai_tests_config["do_cap_test"][
                    "suspect_threshold"
                ],
                fail_threshold=hakai_tests_config["do_cap_test"]["fail_threshold"],
                ratio_above_threshold=hakai_tests_config["do_cap_test"][
                    "ratio_above_threshold"
                ],
                minimum_bins_per_profile=hakai_tests_config["do_cap_test"][
                    "minimum_bins_per_profile"
                ],
            )

    # Add a Missing Flag at Position when latitude/longitude are NaN. For some reasons, QARTOD is missing that.
    print("Flag Missing Position Records")
    df.loc[df["latitude"].isna(), "position_unknown_location"] = QartodFlags.UNKNOWN
    df.loc[df["longitude"].isna(), "position_unknown_location"] = QartodFlags.UNKNOWN

    # BOTTOM HIT DETECTION
    #  Find Profiles that were flagged near the bottom and assume this is likely related to having it the bottom.
    if "bottom_hit_detection" in hakai_tests_config:
        print("Flag Bottom Hit Data")
        df = hakai_tests.bottom_hit_detection(
            df,
            variable=hakai_tests_config["bottom_hit_detection"]["variable"],
            profile_id=profile_id,
            depth_variable=zinp,
            profile_direction_variable=direction_flag,
        )

    # Detect PAR Shadow
    if "par_shadow_test" in hakai_tests_config:
        print("Flag PAR Shadow Data")
        df = hakai_tests.par_shadow_test(
            df,
            variable=hakai_tests_config["par_shadow_test"]["variable"],
            min_par_for_shadow_detection=hakai_tests_config["par_shadow_test"][
                "min_par_for_shadow_detection"
            ],
            profile_id=profile_id,
            direction_flag=direction_flag,
            depth_var=zinp,
        )

    # APPLY QARTOD FLAGS FROM ONE CHANNEL TO OTHER AGGREGATED ONES
    # Generate Hakai Flags
    for var in tested_variable_list:
        print("Apply flag results to " + var)

        # Extra flags that apply to all variables
        extra_flags = (
            "|bottom_hit_test|qartod_location_test"
            + "|pressure_qartod_gross_range_test|depth_qartod_gross_range_test"
        )

        # Add Density Inversion to selected variables
        if var in ["temperature", "salinity", "conductivity"]:
            extra_flags = extra_flags + "|sigma0_qartod_density_inversion_test"

        # Add DO Cap Flag
        if var in ["dissolved_oxygen_ml_l", "rinko_ml_l"]:
            extra_flags = extra_flags + "|" + var + "_do_cap_test"

        # Create Hakai Flag Columns
        df = get_hakai_flag_columns(df, var, extra_flags)

    # Apply Hakai Grey List
    # Grey List should overwrite the QARTOD Flags
    print("Apply Hakai Grey List")
    df = hakai_tests.grey_list(df)

    return df


def run(
    hakai_id=None,
    station=None,
    filter_variables=True,
    qc_config=None,
    drop_single_test=True,
):
    """
    Method use to retrieve Hakai CTD data from the hakai database throuh the API and then run the different tests requested within the configuration
    """
    # Define dataframe
    filter_by = []
    if hakai_id:
        filter_by += ["hakai_id={" + ",".join(hakai_id) + "}"]

    if station:
        filter_by += ["station=" + ",".join(station)]

    # Filter variables
    if filter_variables:
        filter_by += ["fields=" + ",".join(get.hakai_api_selected_variables)]

    filter_by += ["(status!=MISCAST|status==null)", "limit=-1"]
    df = get.hakai_ctd_data("&".join(filter_by))

    if len(df) == 0:
        warnings.warn("No Data is available for this specific input", RuntimeWarning)
        return None, None

    # Save the list of initial variables
    initial_variable_list = df.columns

    # Get Derived Variables
    print("Add derived variables")
    df = utils.derived_ocean_variables(df)

    # Load default test parameters used right now!=
    if qc_config == None:
        print("Load Default Configuration")
        with open(
            os.path.join(os.path.dirname(__file__), "config", "hakai_ctd_profile.json")
        ) as f:
            qc_config = json.loads(f.read())

    # Get Reference stations ( this should be changed to get it form the database or added to the data table
    hakai_stations = get.hakai_stations()

    # Run all of the tests on each available profile
    df = tests_on_profiles(df, hakai_stations, qc_config)

    # Make sure to include Level 1 and Level 2 flags
    # TODO TEMPORARY
    output_variable_list = []
    for var in initial_variable_list:
        output_variable_list.append(var)
        if var.endswith("_flag"):
            output_variable_list.append(re.sub("_flag$", "", var) + "_qartod_flag")
            output_variable_list.append(re.sub("_flag$", "", var) + "_flag_description")

    # Add position qartod_location_test
    position_flag = df.filter(like="location_test").columns.tolist()
    if position_flag:
        df.rename(
            columns={position_flag[0]: "position_qartod_location_test"}, inplace=True
        )
        output_variable_list += ["position_qartod_location_test"]
    if drop_single_test:
        return df.filter(items=output_variable_list)
    else:
        return df


def get_hakai_flag_columns(
    df,
    var,
    extra_flag_list="",
    flag_values_to_consider=[3, 4],
    level_1_flag_suffix="_qartod_flag",
    level_2_flag_suffix="_flag_description",
):
    """
    Generate the different Level1 and Level2 flag columns by grouping the different tests results.
    """

    def generate_level2_flag(row):
        """
        Regroup together tests results in "flag_value_to_consider" as a json string to be outputed as a level2 flag
        """
        level2 = {
            item: value
            for item, value in row.items()
            if value in flag_values_to_consider
        }
        if level2 == {}:
            return ""
        else:
            return str(level2)

    # Retrieve each flags column associated to a variable
    var_flag_results = df.filter(regex=var + "_" + extra_flag_list)

    # Drop Hakai already existing flags, this will be dropped once we get the right flag columns
    #  available on the database side
    var_flag_results = var_flag_results.drop(var + "_flag", axis=1, errors="ignore")

    # Generete Level 1 Aggregated flag columns
    df[var + level_1_flag_suffix] = qartod_compare(
        var_flag_results.transpose().to_numpy()
    )

    # Generete Level 2 Flag Description for failed flag
    df[var + level_2_flag_suffix] = var_flag_results.apply(
        generate_level2_flag, axis="columns"
    )

    # Make sure that empty records are flagged as MISSING
    if var in df:
        df.loc[df[var].isna(), var + level_1_flag_suffix] = QartodFlags.MISSING
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-hakai_id")
    parser.add_argument("-station")
    args = parser.parse_args()

    # Read json file or json string
    if args.station:
        stations = args.station.split(",")
        print(f"Review stations: {stations}")
    else:
        stations = None
    if args.hakai_id:
        hakai_ids = args.hakai_id.split(",")
        print(f"Review hakai_ids: {hakai_ids}")
    else:
        hakai_ids = None

    # Run Query
    df = run(station=stations, hakai_id=hakai_ids)