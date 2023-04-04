from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import dotenv_values

config = dotenv_values(".env")  # load shared development variables
engine = create_engine(
    f"postgresql+psycopg2://{config['POSTGRES_USERNAME']}:{config['POSTGRES_PASSWORD']}@{config['POSTGRES_HOST']}:{config['POSTGRES_PORT']}/{config['POSTGRES_DATABASE_NAME']}",
    connect_args={"connect_timeout": 120},
)

with engine.connect( ) as conn:
    df = pd.read_sql('SELECT top 10 * FROM ctd.ctd_file_cast_data')

def get_station_range_depth_test():
    # with open("review/get_depth_in_station_range_test_results.sql") as query_file:
    #     query = query_file.read()

    # with engine.connect() as con:
    #     df = pd.read_sql(query, con=con)
    df = pd.read_csv("review/results.csv")
    station_info = pd.read_csv(
        "hakai_profile_qc/StationLocations.csv", delimiter=";"
    ).rename(columns={"Station": "station"})
    df = station_info[["station", "Bot_depth", "Bot_depth_GIS"]].merge(
        df, how="right", on="station"
    )

    return df


if __name__ == "__main__":
    df = get_station_range_depth_test()
    with open("review/get_depth_in_station_range_test.md", "w") as result_file:
        df.to_markdown(result_file)
