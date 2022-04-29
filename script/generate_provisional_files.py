from hakai_api import Client
import hakai_profile_qc.review

import numpy as np
import pandas as pd
import argparse
import json
from tqdm import tqdm
import re
import os

import logging

logger = logging.getLogger()
logging.basicConfig(filename='provisional_conversion.log', level=logging.ERROR)

def rename_columns(col):
    if col in ['direction_flag']:
        return col
    col = re.sub('_flag$','_flag_description',col)
    col = re.sub('_flag_level_1$','_qartod_flag',col)
    return col

CHUNK_SIZE=300

def qc_station(station):
    # Run QC tests
    df = hakai_profile_qc.review.run_tests(station=station, filter_variables=True)
    
    # Replace flag values from seabird
    df = df.replace({-9.99E-29: np.nan})

    # Consider only downcast data
    df['direction_flag'] = df['direction_flag'].fillna('d')
    df = df.query("direction_flag=='d'") # Ignore up cast and static data in provisional dataset

    # Rename Columns 
    df.columns = [rename_columns(col) for col in df.columns]
    df = df.drop(columns=['weather','bin_stats'])

    # Save data grouped xarray datasets just to serve temporarily ERDDAP
    for (work_area,station),df_profile in tqdm(df.groupby(['work_area','station']),desc='Save each individual files:',unit='file'):
        dir_path = os.path.join(output_path,work_area,station)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        start_time = pd.to_datetime(df_profile['start_dt'].min())
        end_time = pd.to_datetime(df_profile['start_dt'].min())
        file_output = os.path.join(dir_path, f"{work_area}_{station}_{start_time.strftime('%Y%m%d')}-{end_time.strftime('%Y%m%d')}.nc")
        df_profile.to_xarray().to_netcdf(file_output)


parser = argparse.ArgumentParser(description="QC Hakai CTD Profiles")
parser.add_argument(
    "--output_path",
    type=str,
    help="Which database is run the script",
    default="./output",
)
args = parser.parse_args()
output_path = args.output_path

# Connect to API
client = Client()

ctd_cast_endpoint = "/ctd/views/file/cast"
ctd_cast_data_endpoint = "/ctd/views/file/cast/data"

# Get Cast Data
processed_cast_filter = "processing_stage={8_rbr_processed,8_binAvg,9_qc_auto,10_qc_pi}&status==null&station_latitude!=null&station_longitude!=null&work_area={CALVERT,QUADRA,JOHNSTONE STRAIT}&limit=-1&fields=work_area,station,hakai_id,start_dt"
url = f"{client.api_root}{ctd_cast_endpoint}?{processed_cast_filter}"
response = client.get(url)
df_stations = pd.DataFrame(response.json()).sort_values(['work_area','station','start_dt']).groupby(['work_area','station']).agg({'start_dt':['min','max'],'hakai_id':['count']})


is_low_count_station = df_stations[('hakai_id','count')]<5
low_count_cast_stations = df_stations.loc[is_low_count_station]

# Run all the stations with a low count all at by 20 at the time
low_count_station_list = low_count_cast_stations.index.get_level_values(1).to_list()
for station_list in np.array_split(low_count_station_list, round(len(low_count_cast_stations)/30)):
    try:
        qc_station(list(station_list))
    except:
        try:
            for station in station_list:
                qc_station([station])
        except:
            logger.error(f'Failed to output {station}')

# Then iterate over the stations with more drop by station
for work_area,station,row in df_stations[not is_low_count_station].iterrows():
    qc_station([station])
