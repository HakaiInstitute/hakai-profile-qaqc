from pathlib import Path

from hakai_ctd_qc import hakai_tests
from hakai_ctd_qc.__main__ import _convert_time_to_datetime, _derived_ocean_variables
from hakai_ctd_qc.variables import HAKAI_TEST_SUITE
from tests.hakai_ids_with_issues import HAKAI_IDS_WITH_ISSUES

MODULE_PATH = Path(__file__).parent


def test_local_suite_has_all_hakai_ids(df_initial):
    available_hakai_ids = df_initial["hakai_id"].unique()
    missing_hakai_ids = [
        hakai_id for hakai_id in HAKAI_TEST_SUITE if hakai_id not in available_hakai_ids
    ]
    assert missing_hakai_ids == [], "Local test suite is missing %s hakai_ids= %s" % (
        len(missing_hakai_ids),
        missing_hakai_ids,
    )


class TestDerivedVariables:
    def test_derive_variables_from_local(self, df_local):
        df_temp = _derived_ocean_variables(df_local)
        derived_variables = [
            "conservative_temperature",
            "sigma0",
            "absolute_salinity",
            "density",
        ]
        missing_derieved_variables = [
            var for var in derived_variables if var not in df_temp.columns
        ]
        assert (
            missing_derieved_variables != []
        ), f"missing derived variables {missing_derieved_variables}"


class TestTimeConversion:
    def test_full_dataframe_timeconversion(self, df_local):
        df_temp = _convert_time_to_datetime(df_local)
        assert isinstance(
            df_temp["start_dt"].dtype, object
        ), "Dataframe start_dt is not a datetime object"


class TestHakaiBadValueTests:
    def test_seabird_hakai_bad_value_test(self, df_initial, df_local):
        df = df_initial.query("hakai_id == '01907674_2016-10-20T16:29:29Z'")
        assert (
            (df == -9.99e-29).any().any()
        ), "No seabird flag value -9.99E-29 is present in local test suite"

        df_flagged = df_local.loc[df.loc[(df == -9.99e-29).any(axis=1)].index]
        flagged_columns = [
            "descent_rate",
            "conductivity",
            "temperature",
            "depth",
            "par",
            "flc",
            "turbidity",
            "salinity",
            "dissolved_oxygen_ml_l",
            # "oxygen_voltage",
        ]
        assert (
            df_flagged.filter(regex="|".join(flagged_columns)).filter(
                regex="hakai_bad_value_test$"
            )
            == 4
        ).all(axis=None), "Not all the values -9.99E-29 were not flagged as FAIL=4"
        assert (
            (
                df_flagged.filter(regex="|".join(flagged_columns)).filter(
                    regex="_flag_level_1$"
                )
                == 4
            )
            .all(axis=None)
            .all()
        ), "Not all the values -9.99E-29 were not flagged as *_flag_level_1=FAIL(=4)"
        assert (
            df_flagged.filter(regex="|".join(flagged_columns))
            .filter(regex="_flag$")
            .map(lambda x: str(x).startswith("SVD"))
            .all(axis=None)
        ), "Not all the values -9.99E-29 were not flagged as *_flag=SVD"
        assert (
            df_flagged.filter(regex="|".join(flagged_columns))
            .filter(regex="_flag$")
            .map(lambda x: "hakai_bad_value_test" in str(x))
            .all(axis=None)
        ), "Not all the values -9.99E-29 *_flag column contains the expression 'hakai_bad_value_test'"

    def test_missing_whole_profile_bad_value_test(self, df_local):
        df = df_local.query("hakai_id == '01907674_2018-10-31T19:10:18Z'")
        assert (
            not df.empty
        ), "Missing hakai_id=='01907674_2018-10-31T19:10:18Z' from local test suite"
        assert (
            df["dissolved_oxygen_ml_l_hakai_bad_value_test"] == 9
        ).all(), "Not all oxygen missing bad_value_test are flagged as MISSING=9"
        assert (
            df.loc[
                df["dissolved_oxygen_ml_l_hakai_bad_value_test"] == 9,
                "dissolved_oxygen_ml_l_flag_level_1",
            ]
            == 9
        ).all(), "Not all oxygen missing bad_value_test are flagged as MISSING=9"

    def test_missing_value_bad_value_test(self, df_local):
        for variable in df_local.columns:
            qartod_flag_variable = f"{variable}_hakai_bad_value_test"
            if qartod_flag_variable in df_local.columns:
                assert all(
                    df_local.loc[df_local[variable].isna(), qartod_flag_variable].isin(
                        [4, 9]
                    )
                ), f"Not all '{variable}'.isna() is flagged as FAIL=4 or MISSING=9"

                is_bad_value_flagged = df_local[qartod_flag_variable].isin([4, 9])
                assert (
                    df_local.loc[is_bad_value_flagged, qartod_flag_variable]
                    == df_local.loc[is_bad_value_flagged, f"{variable}_flag_level_1"]
                ).all(), "Bad value flag isn't matching flag_level_1"


class TestHakaiQueryTests:
    def test_nature_trust_mid_sensors_submerged_flags(self, df_local):
        query = "organization=='NATURE TRUST' and sensors_submerged=='Mid'"
        df = df_local.query(query)
        assert not df.empty, "Missing {query}"
        assert (
            df["par_hakai_sensor_mid_submerged_test"] == 4
        ).all(), "Failed to flag nature trust par sensors_submberged=='Mid' -> 4"
        assert (
            df["par_flag"].str.startswith("SVD").all()
        ), "Failed to flag the par_flag to SVD"
        assert (
            df["dissolved_oxygen_ml_l_flag_level_1"].isin([1, 9]).all()
        ), "Failed to flag the dissolved_oxygen_ml_l_flag_level_1 to GOOD=1"
        assert (
            df["dissolved_oxygen_ml_l_flag"].isna()
        ).all(), "Failed to flag dissolved_oxygen_ml_l_flag_level_1 to AV (empty)"
        assert (
            df["dissolved_oxygen_percent_flag_level_1"].isin([1, 9]).all()
        ), "Failed to flag the dissolved_oxygen_percent_flag_level_1 to GOOD=1"
        assert (
            df["dissolved_oxygen_percent_flag"].isna()
        ).all(), "Failed to flag dissolved_oxygen_percent_flag to AV (empty)"

    def test_nature_trust_bottom_sensors_submerged_flags(self, df_local):
        query = "organization=='NATURE TRUST' and sensors_submerged=='Bottom'"
        df = df_local.query(query)
        assert not df.empty, "Missing {query}"
        for var in ["par", "dissolved_oxygen_ml_l", "dissolved_oxygen_percent"]:
            assert (
                (df[f"{var}_hakai_sensor_bottom_submerged_test"] == 4)
                | (df[var].isna())
            ).all(), (
                f"Failed to flag nature trust {var} sensors_submberged=='Bottom' -> 4"
            )
            assert (
                (df[f"{var}_flag"].str.startswith("SVD") | (df[var].isna())).all()
            ).all(), f"Failed to flag the {var}_flag to SVD"
            assert (
                (df[f"{var}_flag_level_1"] == 4) | (df[var].isna())
            ).all(), f"Failed to flag the {var}_flag_level_1 to 4"


class TestHakaiDOCapTest:
    def test_do_cap_static_drop(self, df_local):
        hakai_tests.do_cap_test(
            df_local.query("direction_flag=='s'"), "dissolved_oxygen_ml_l"
        )

    def test_do_cap_test_svd_locally(self, df_local):
        assert "dissolved_oxygen_ml_l_hakai_do_cap_test" in df_local.columns, (
            "Missing dissolved_oxygen_ml_l_hakai_do_cap_test from dataframe: %s"
            % df_local.filter(like="dissolved_oxygen").columns
        )
        df = df_local.query("dissolved_oxygen_ml_l_hakai_do_cap_test==4")
        assert (
            not df.empty
        ), "No hakai_id has dissolved_oxygen_ml_l_hakai_do_cap_test=FAIL=4)"
        assert all(
            hakai_id in df_local["hakai_id"].values
            for hakai_id in HAKAI_IDS_WITH_ISSUES["do_cap_fail_hakai_ids"]
        ), "Not all do cap test failed profiles are present"
        not_flagged_do_cap_failed = [
            hakai_id
            for hakai_id in HAKAI_IDS_WITH_ISSUES["do_cap_fail_hakai_ids"]
            if hakai_id not in df["hakai_id"].values
        ]
        assert not any(
            not_flagged_do_cap_failed
        ), f"The following hakai_ids do cap test weren't flagged as FAIl: {not_flagged_do_cap_failed}"
        assert (
            df["dissolved_oxygen_ml_l_hakai_do_cap_test"].isin([4]).all()
        ), "Not all the dissolved_oxygen_ml_l_hakai_do_cap_test failed hakai_ids were flagged as FAIL=4"
        assert (
            df["dissolved_oxygen_ml_l_flag"].str.startswith("SVD").all()
        ), "Not all the dissolved_oxygen_ml_l_flag failed hakai_ids were flagged as SVD"
        assert (
            df["dissolved_oxygen_ml_l_flag_level_1"].isin([4]).all()
        ), "Not all the dissolved_oxygen_ml_l_flag_level_1 failed hakai_ids were flagged as FAIL=4"


class TestQARTODTests:
    def test_gross_range_results(self, df_local):
        df = df_local.query("hakai_id == '01907674_2016-10-18T18:09:33Z'")
        assert (
            not df.empty
        ), "Missing test hakai_id=='01907674_2016-10-18T18:09:33Z' in local test suite"
        assert (
            len(df.loc[df["dissolved_oxygen_ml_l_qartod_gross_range_test"] == 4]) == 249
        ), "Missing qartod gross range result in dissolved_oxygen_ml_l_flag_level_1"
        assert (
            df.loc[
                df["dissolved_oxygen_ml_l_qartod_gross_range_test"] == 4,
                "dissolved_oxygen_ml_l_flag_level_1",
            ]
            == 4
        ).all(), (
            "Missing qartod gross range result in dissolved_oxygen_ml_l_flag_level_1"
        )

        assert (
            df.loc[
                df["dissolved_oxygen_ml_l_qartod_gross_range_test"] == 4,
                "dissolved_oxygen_ml_l_flag",
            ].str.contains("SVD: dissolved_oxygen_ml_l_qartod_gross_range_test")
        ).all(), (
            "Missing qartod gross range result in dissolved_oxygen_ml_l_flag_level_1"
        )


class TestProcessLogTestsWarning:
    def test_slow_oxygen_warning(self, df_local):
        """Review the results of the slow oxygen sensor test"""
        assert (
            "dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test" in df_local.columns
        ), (
            "Missing dissolved_oxygen_ml_l_slow_oxygen_sensor_test from dataframe: %s"
            % df_local.filter(like="dissolved_oxygen").columns
        )
        assert (
            df_local["dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test"]
            .isin([3])
            .any()
        ), (
            "Not any of the dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test"
            " failed hakai_ids were flagged as WARNING=3"
        )
        flagged_hakai_ids = df_local.query(
            "dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test==3"
        )["hakai_id"].values
        assert all(
            df_local.query("dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test==3")[
                "dissolved_oxygen_ml_l_flag"
            ].str.contains("SVC: dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test")
        ), "Not all dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test were flagged as SVC"
        assert all(
            df_local.query("dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test==3")[
                "dissolved_oxygen_ml_l_flag_level_1"
            ].isin([3, 4])
        ), "Not all dissolved_oxygen_ml_l_hakai_slow_oxygen_sensor_test were flagged as WARNING=3 or greater"
        assert all(
            item in flagged_hakai_ids
            for item in HAKAI_IDS_WITH_ISSUES["slow_oxygen_warning_hakai_ids"]
        ), "Not all slow oxygen sensor test failed profiles are present"

    def test_no_soak_warning(self, df_local):
        """Review the results of the no soak test"""
        assert (
            df_local["dissolved_oxygen_ml_l_hakai_no_soak_test"].isin([3]).any()
        ), "Not any of the hakai_no_soak_flag failed hakai_ids were flagged as WARNING=3"
        assert all(
            df_local.query("dissolved_oxygen_ml_l_hakai_no_soak_test==3")[
                "dissolved_oxygen_ml_l_flag"
            ].str.contains("SVC: dissolved_oxygen_ml_l_hakai_no_soak_test")
        ), "Not all hakai_no_soak_flag were flagged as SVC"
        assert all(
            df_local.query("dissolved_oxygen_ml_l_hakai_no_soak_test==3")[
                "dissolved_oxygen_ml_l_flag_level_1"
            ].isin([3, 4])
        ), "Not all dissolved_oxygen_ml_l_hakai_no_soak_test were flagged as WARNING=3 or greater"

        flagged_hakai_ids = set(
            df_local.query("dissolved_oxygen_ml_l_hakai_no_soak_test==3")[
                "hakai_id"
            ].values
        )
        assert all(
            item in flagged_hakai_ids
            for item in HAKAI_IDS_WITH_ISSUES["no_soak_warning_hakai_ids"]
        ), "Not all slow oxygen sensor test failed profiles are present"

        # make sure that temperature, salinity,conductivity are also flagged
        assert all(
            df_local.query("temperature_hakai_no_soak_test==3")[
                "temperature_flag"
            ].str.contains("SVC: temperature_hakai_no_soak_test")
        ), "Not all hakai_no_soak_flag were flagged as SVC"
        assert all(
            df_local.query("temperature_hakai_no_soak_test==3")[
                "temperature_flag_level_1"
            ].isin([3, 4])
        ), "Not all hakai_no_soak_flag were flagged as WARNING=3 or greater"
        assert all(
            df_local.query("salinity_hakai_no_soak_test==3")[
                "salinity_flag"
            ].str.contains("SVC: salinity_hakai_no_soak_test")
        ), "Not all hakai_no_soak_flag were flagged as SVC"
        assert all(
            df_local.query("salinity_hakai_no_soak_test==3")[
                "salinity_flag_level_1"
            ].isin([3, 4])
        ), "Not all hakai_no_soak_flag were flagged as WARNING=3 or greater"
        assert all(
            df_local.query("conductivity_hakai_no_soak_test==3")[
                "conductivity_flag"
            ].str.contains("SVC: conductivity_hakai_no_soak_test")
        ), "Not all hakai_no_soak_flag were flagged as SVC"
        assert all(
            df_local.query("conductivity_hakai_no_soak_test==3")[
                "conductivity_flag_level_1"
            ].isin([3, 4])
        ), "Not all hakai_no_soak_flag were flagged as WARNING=3 or greater"

    def test_short_static_deployment(self, df_local):
        """Review the results of the short static deployment test"""
        assert (
            df_local["hakai_short_static_deployment_test"].isin([3]).any()
        ), "Not any of the hakai_short_static_deployment_test failed hakai_ids were flagged as WARNING=3"
        assert all(
            df_local.query("hakai_short_static_deployment_test==3")[
                "dissolved_oxygen_ml_l_flag"
            ].str.contains("SVC: hakai_short_static_deployment_test")
        ), "Not all hakai_short_static_deployment_test were flagged as SVC"
        assert all(
            df_local.query("hakai_short_static_deployment_test==3")[
                "dissolved_oxygen_ml_l_flag_level_1"
            ].isin([3, 4, 9])
        ), "Not all hakai_short_static_deployment_test were flagged as WARNING=3 or greater"

        flagged_hakai_ids = set(
            df_local.query("hakai_short_static_deployment_test==3")["hakai_id"].values
        )
        missing_short_static_deployment = [
            hakai_id
            for hakai_id in HAKAI_IDS_WITH_ISSUES["short_static_deployment"]
            if hakai_id not in flagged_hakai_ids
        ]
        assert not missing_short_static_deployment, (
            "Not all short static deployment failed profiles are present. Missing: %s"
            % missing_short_static_deployment
        )
