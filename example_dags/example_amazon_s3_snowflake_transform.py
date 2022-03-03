"""
Copyright Astronomer, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
from datetime import datetime, timedelta

import pandas as pd

# Uses data from https://www.kaggle.com/c/shelter-animal-outcomes
from airflow.decorators import dag

from astro import dataframe as df
from astro import sql as aql
from astro.sql.table import Table


@aql.transform()
def combine_data(center_1: Table, center_2: Table):
    return """SELECT * FROM {{center_1}}
    UNION SELECT * FROM {{center_2}}"""


@aql.transform()
def clean_data(input_table: Table):
    return """SELECT *
    FROM {{input_table}} WHERE TYPE NOT LIKE 'Guinea Pig'
    """


@df
def aggregate_data(df: pd.DataFrame):
    adoption_reporting_dataframe = df.pivot_table(
        index="DATE", values="NAME", columns=["TYPE"], aggfunc="count"
    ).reset_index()

    return adoption_reporting_dataframe


@dag(
    start_date=datetime(2021, 1, 1),
    max_active_runs=1,
    schedule_interval="@daily",
    default_args={
        "email_on_failure": False,
        "retries": 0,
        "retry_delay": timedelta(minutes=5),
    },
    catchup=False,
)
def example_amazon_s3_snowflake_transform():
    combined_data = combine_data(
        center_1=Table(
            "ADOPTION_CENTER_1",
            database=os.environ["SNOWFLAKE_DATABASE"],
            schema=os.environ["SNOWFLAKE_SCHEMA"],
            conn_id="snowflake_conn",
        ),
        center_2=Table(
            "ADOPTION_CENTER_2",
            database=os.environ["SNOWFLAKE_DATABASE"],
            schema=os.environ["SNOWFLAKE_SCHEMA"],
            conn_id="snowflake_conn",
        ),
    )

    cleaned_data = clean_data(combined_data)
    aggregated_data = aggregate_data(
        cleaned_data,
        output_table=Table(
            "aggregated_adoptions",
            schema=os.environ["SNOWFLAKE_SCHEMA"],
            conn_id="snowflake_conn",
        ),
    )


dag = example_amazon_s3_snowflake_transform()