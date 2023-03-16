import os

import numpy as np
import pandas as pd
import pytest

from hakai_profile_qc import hakai_tests
from hakai_profile_qc.__main__ import _derived_ocean_variables, run_qc_profiles

MODULE_PATH = os.path.dirname(__file__)
df_local = pd.read_parquet(f"{MODULE_PATH}/test_data/ctd_test_suite.parquet")
df_local = _derived_ocean_variables(df_local)
df_local = run_qc_profiles(df_local)


@pytest.mark.parametrize(
    "value,flag", [(-9.99e-29, 4), (None, 9), (pd.NA, 9), (np.nan, 9)]
)
class TestHakaiBadValues:
    def test_trailing_bad_value(self, value, flag):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, value]})
        df = hakai_tests.bad_value_test(df, "x")

        assert (
            df.iloc[-1]["x_hakai_bad_value_test"] == flag
        ), "Failed to flag -9.99E-29 value as FAIL=4"
        assert (
            df.iloc[:-1]["x_hakai_bad_value_test"] == 1
        ).all(), "Other records were not flag as GOOD=1"

    def test_first_bad_value(self, value, flag):
        df = pd.DataFrame({"x": [value, 1, 2, 3, 4, 5, 6, 7]})
        df = hakai_tests.bad_value_test(df, "x")

        assert (
            df.iloc[0]["x_hakai_bad_value_test"] == flag
        ), "Failed to flag -9.99E-29 value as FAIL=4"
        assert (
            df.iloc[1:]["x_hakai_bad_value_test"] == 1
        ).all(), "Other records were not flag as GOOD=1"

    def test_multiple_bad_values(self, value, flag):
        df = pd.DataFrame({"x": [value, 1, value, value, 4, 5, 6, 7]})
        df = hakai_tests.bad_value_test(df, "x")

        assert (
            df.iloc[[0, 2, 3]]["x_hakai_bad_value_test"] == flag
        ).all(), "Failed to flag -9.99E-29 value as FAIL=4"
        assert (df.iloc[4:]["x_hakai_bad_value_test"] == 1).all() & (
            df.iloc[1]["x_hakai_bad_value_test"] == 1
        ), "Other records were not flag as GOOD=1"


class TestEmptyInput:
    def test_empty_dataframe_bad_values(self):
        df = pd.DataFrame({"x": []})
        df = hakai_tests.bad_value_test(df, "x")
        assert "x_hakai_bad_value_test" in df, "New flag column was not generated"