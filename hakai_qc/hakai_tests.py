import pandas as pd
import numpy as np
from ioos_qc.qartod import QartodFlags
import warnings
import pkg_resources
from . import get


def do_cap_test(df,
                var,
                profile_id,
                direction_flag,
                depth_var,
                bin_size=1,
                suspect_threshold=.2,
                fail_threshold=0.5,
                ratio_above_threshold=0.5,
                minimum_bins_per_profile=10,
                flag_name='_do_cap_test'
                ):
    """
    Hakai do_cap_test compare down and up cast values measured by an instrument at the same depth. The test compare
    the number of records that has a different value above the suspect or fail threshold versus the total number of
    similar value available for each cast. If n_suspect/n_values is above suspect/fail threshold, the whole profile
    is flagged accordingly.

    INPUTS:
    df: dataframe
    var: variable to review up/down cast values
    depth_var: variable describing the vertical coordinate
    direction_flag: variable describing the direction of the profile
    bin_size: vertical bin size to apply the test to
    suspect_threshold: suspect threshold value for detection |X_nu - X_nd|
    fail_threshold: suspect threshold value for detection |X_nu - X_nd|
    ratio_above_threshold: minimum threshold of fraction of suspect/fail binned value to consider to flag profile
    minimum_bins_per_profile: minimum amount of bins necessary to make the test usable.

    ASSUMPTIONS:
    As of now, the test assume that the input data is already bin averaged for either up or downcast.

    OUTPUT:
    The test will generate an extra column [var]_do_cap_test with QARTOD flag.
    """
    # Handle empty inputs or with no upcast data.
    if df[var].isna().all():
        df[var + flag_name] = QartodFlags.MISSING
        return
    elif all(df.groupby(by=[profile_id, depth_var])[var].count() <= 1):  # All the profiles are bad or unknown
        # Find the maximum count of matching pressure bin per profile_id
        hakai_id_matching_depth = df.groupby(by=[profile_id, depth_var])[var].count().groupby(by=profile_id).max()
        if not hakai_id_matching_depth.isin([0, 1]).all():
            assert RuntimeWarning, 'matching pressure bin count is different than 0 or 1'
        for unknown_id in hakai_id_matching_depth[hakai_id_matching_depth == 1].index.to_list():
            df.loc[df[profile_id] == unknown_id, var+flag_name] = QartodFlags.UNKNOWN
        for missing_id in hakai_id_matching_depth[hakai_id_matching_depth == 0].index.to_list():
            df.loc[df[profile_id] == missing_id, var+flag_name] = QartodFlags.MISSING
        return

    # Assign each record to a specific bin id
    df['bin_id'] = (df[depth_var] / bin_size).round()

    # Group average record associated to each profile,direction and bin_id
    df_grouped = df.groupby([profile_id, direction_flag, 'bin_id']).mean()

    # Count how many values are available for each profile and pressure bin and get their range max-min (ptp)
    profile_bin_stats = df_grouped.groupby(by=[profile_id, 'bin_id'])[var].agg([np.ptp, 'count'])

    profile_bin_stats['is_missing'] = profile_bin_stats['ptp'].isnull() & \
                                      (profile_bin_stats['count'] == 0)  # no value available

    # Difference between values higher than thresholds
    profile_bin_stats['is_suspect'] = (profile_bin_stats['ptp'] > suspect_threshold) & \
                                      (profile_bin_stats['count'] > 1)
    profile_bin_stats['is_fail'] = (profile_bin_stats['ptp'] > fail_threshold) & \
                                   (profile_bin_stats['count'] > 1)
    profile_bin_stats['is_unknown'] = profile_bin_stats['count'] == 1  # Only downcast or upcast available

    # Sum each flag per depth bin for each profiles per profile
    profile_stats = profile_bin_stats.groupby(by=[profile_id]).sum()

    # Get the amount of the vertical bin available total and the amount with value in up and downcast
    profile_stats['nBinsPerProfile'] = profile_bin_stats['ptp'].replace({pd.NA: -1}).groupby(by=[profile_id]).count()
    profile_stats['nGoodBinsPerProfile'] = profile_bin_stats[profile_bin_stats['ptp'] > 0]['ptp'] \
        .groupby(by=[profile_id]).count()

    # Get Ratio of each flag generated vs the amount of bins available
    for flag_test in ['is_unknown', 'is_suspect', 'is_fail', 'is_missing']:
        profile_stats[flag_test + '_ratio'] = profile_stats[flag_test] / profile_stats['nGoodBinsPerProfile']

    # Detect profiles for which test can be applied (missing up or downcast or not enough vertical bins)
    unknown_profile_id = profile_stats.index[
        (profile_stats['nGoodBinsPerProfile'] < minimum_bins_per_profile) |
        (profile_stats['nGoodBinsPerProfile'].isnull())]

    # Get the list of index for each flag type
    suspect_profile_id = profile_stats[(profile_stats['is_suspect_ratio'] > ratio_above_threshold)].index
    fail_profile_id = profile_stats[(profile_stats['is_fail_ratio'] > ratio_above_threshold)].index
    missing_profile_id = profile_stats[(profile_stats['nGoodBinsPerProfile'].isnull()) &
                                       (profile_stats['is_missing'] == profile_stats['nBinsPerProfile'])].index

    # Start with everything passing
    df[var + flag_name] = QartodFlags.GOOD
    if any(suspect_profile_id):
        df.loc[df[profile_id].isin(suspect_profile_id), var + flag_name] = QartodFlags.SUSPECT
    if any(fail_profile_id):
        df.loc[df[profile_id].isin(fail_profile_id), var + flag_name] = QartodFlags.FAIL
    if any(unknown_profile_id):
        df.loc[df[profile_id].isin(unknown_profile_id), var + flag_name] = QartodFlags.UNKNOWN
    if any(missing_profile_id):
        df.loc[df[profile_id].isin(missing_profile_id), var + flag_name] = QartodFlags.MISSING
    return df


def bottom_hit_detection(df,
                         variable,
                         profile_id='hakai_id',
                         depth_variable='depth',
                         profile_direction_variable='direction_flag',
                         flag_column_name='bottom_hit_test'):
    """
    Method that flag consecutive data near the bottom of a profile that was flagged SUSPECT=3 or FAIl=4. Output a
    'bottom_hit_flag' channel.
    """

    # For each profile (down and up cast), get the density flag value for the deepest record.
    #  If flagged [3,4], it has likely hit the bottom.
    df[flag_column_name] = QartodFlags.GOOD

    bottom_hit_id = df.sort_values(by=[profile_id, profile_direction_variable, depth_variable]) \
        .groupby(by=[profile_id, profile_direction_variable]) \
        .last()[variable].isin([QartodFlags.SUSPECT, QartodFlags.FAIL])

    # Now let's flag the consecutive data that are flagged in sigma0 near the bottom as bottom hit
    for hakai_id in bottom_hit_id[bottom_hit_id].reset_index()[profile_id]:
        for index, df_bottom_hit in df[df[profile_id] == hakai_id].groupby(by=[profile_id,
                                                                               profile_direction_variable]):
            # For each bottom hit find the deepest good record in density and flag everything else below as FAIL
            df.loc[df_bottom_hit[df_bottom_hit[depth_variable] >
                                 df_bottom_hit[df_bottom_hit[variable] == 1][depth_variable].max()].index,
                   flag_column_name] = QartodFlags.FAIL
    return df


def par_shadow_test(df,
                    variable='par',
                    min_par_for_shadow_detection=5,
                    profile_id='hakai_id',
                    direction_flag='direction_flag',
                    depth_var='depth',
                    flag_column_name='par_shadow_test'
                    ):
    """
    The PAR shadow test assume that PAR values should always be increasing with shallower depths. The tool first
    sort the data along the pressure for each individual profiles and compute the cumulative maximum value recorded
    from the bottom to the surface. A PAR value is flagged as SUSPECT if the value is bigger than the
    min_par_for_shadow_detection provided value and lower than the cumulative maximum value.
    """
    # Detect PAR Shadow
    print('Flag PAR Shadow Data')
    if df[variable].isna().all():
        df[flag_column_name] = QartodFlags.UNKNOWN
    else:
        df['par_cummax'] = df.sort_values(by=[profile_id, direction_flag, depth_var], ascending=False).groupby(
            by=[profile_id, direction_flag])[variable].cummax()

        df[flag_column_name] = QartodFlags.GOOD
        df.loc[(df[variable] < df['par_cummax']) & (
                df['par_cummax'] > min_par_for_shadow_detection), flag_column_name] = QartodFlags.SUSPECT
        df.drop('par_cummax', axis=1, inplace=True)
    return df


def bad_value_test(df,
                   variable,
                   flag_list=None,
                   flag_column_suffix='_hakai_bad_value_test'):
    """
    Find Flag values present in the data, attach a FAIL QARTOD Flag to them and replace them by NaN.
    Hakai database ingested some seabird flags -9.99E-29 which need to be recognized and removed.
    """
    # Default Hakai Bad data
    if flag_list is None:
        flag_list = ['.isna', -9.99E-29]

    for flag in flag_list:
        for column in variable:
            # Identify already identified as empty values
            if flag == '.isna':
                is_flagged = df[column].isna()
            else:
                is_flagged = df[column].isin([flag])

            if any(is_flagged):
                df[column + flag_column_suffix] = QartodFlags.GOOD
                df.loc[is_flagged, column + flag_column_suffix] = QartodFlags.MISSING

    # Replace bad data in dataframe to an empty value
    df = df.replace(flag_list, pd.NA)
    return df


def grey_list(df,
              level1_flag_suffix='_qartod_flag',
              level2_flag_suffix='_flag_description',
              grey_list_suffix='_grey_list_test',
              time='measurement_dt'):

    temporary_time_variable = 'temp_time'
    # # Retrieve the grey list data from the Hakai Database
    # endpoint = 'eims/views/output/ctd_flags'
    # df_grey_list, url = get.hakai_ctd_data('', endpoint=endpoint)

    # Retrieve Grey List from Hakai-Profile-Dataset-Grey-List.csv file saved within the package
    grey_var_format = {'device_model': str, 'device_sn': str, 'hakai_id': str, 'query': str, 'data_type': str,
                       'flag_type': int}
    grey_list_path = "HakaiProfileDatasetGreyList.csv"
    grey_list_path = pkg_resources.resource_filename(__name__, grey_list_path)
    df_grey_list = pd.read_csv(grey_list_path, dtype=grey_var_format,
                               parse_dates=['start_datetime_range', 'end_datetime_range'])
    df_grey_list = df_grey_list.replace({pd.NA: None})

    # Make sure that the time variable is in datetime format
    if time not in df.select_dtypes('datetimetz').columns:
        df[temporary_time_variable] = pd.to_datetime((df[time]))
    else:
        df[temporary_time_variable] = df[time]

    # Loop through each lines
    # Since the grey list is a manual input it will likely be small amount and looping through
    # each should be good enough for now. We may have to filter the grey list based on the input in the future
    # if the grey list becomes significant.
    for index, row in df_grey_list.iterrows():

        # Detect matching records
        # Time Axis range to flag
        if row['start_datetime_range'] and row['end_datetime_range'] and row['device_model'] and row['device_sn']:
            matching_time_flag = (df[temporary_time_variable] >= row['start_datetime_range']) \
                                 & (df[temporary_time_variable] <= row['end_datetime_range']) \
                                 & (df['device_model'] == row['device_model']) \
                                 & (df['device_sn'].str.endswith(row['device_sn']))
        else:
            matching_time_flag = None

        # Define query for selecting data
        query = []
        if row['hakai_id']:
            query.append('hakai_id in ' + str(row['hakai_id'].split(',')))

        # Vertical range to be flag
        if row['query']:
            query.append(row['query'])

        # Filter data based on time range and query
        if matching_time_flag.any():
            df_to_flag = df[matching_time_flag]
        elif query:
            df_to_flag = df.query(' & '.join(query))
        else:
            df_to_flag = pd.DataFrame()

        # If some data needs to be flagged
        if len(df_to_flag) > 0:
            # Retrieve Columns to add flag to
            variable_list = row['data_type'].split(',')

            # Review if the columns exist
            unknown_variables = set(variable_list)-set(df.columns)
            if unknown_variables:
                warnings.warn(str(list(unknown_variables))+' are not available and will be ignored',
                              category=RuntimeWarning)
                variable_list = list(set(variable_list)-unknown_variables)

            # Retrieve flag columns
            grey_list_test_columns = [var + grey_list_suffix for var in variable_list]
            qartod_columns = [var + level1_flag_suffix for var in variable_list]
            flag_descriptor_columns = [var + level2_flag_suffix for var in variable_list]

            # Add a grey list test column is missing
            missing_grey_list_flag = set(grey_list_test_columns) - set(df.columns)
            if missing_grey_list_flag:
                for var in missing_grey_list_flag:
                    df[var] = QartodFlags.GOOD

            # Add a grey list test variable for helping review
            df.loc[df_to_flag.index, grey_list_test_columns] = row['flag_type']

            # Overwrite Hakai QARTOD Flag
            df.loc[df_to_flag.index, qartod_columns] = row['flag_type']

            # Append to description Flag Comment and name
            grey_flag_description = 'HakaiGreyList: {Flag: ' + str(row['flag_type']) + \
                                    ', Comment: ' + str(row['comments'])
            if row['flagged_by']:
                grey_flag_description = grey_flag_description + ', FlaggedBy: ' + str(row['flagged_by'])

            grey_flag_description = grey_flag_description + '}'

            for column in flag_descriptor_columns:
                df.loc[df_to_flag.index, column] = df.loc[df_to_flag.index, column].astype(str).str.replace('\}$', '') \
                                                   + grey_flag_description + '}'

    # Remove the temporary time variable
    df = df.drop(temporary_time_variable, axis=1)
    return df
