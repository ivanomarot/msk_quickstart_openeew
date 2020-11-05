#!/usr/bin/env python3
"""
Send JSON data sequentially from the Openeew public dataset to Kafka for a number of periods in minutes.
"""

import json
import pause
from datetime import datetime, timedelta

import defopt
import boto3
import pandas as pd
from openeew.data.aws import AwsDataClient
from openeew.data.df import get_df_from_records
from kafka import KafkaProducer
# Uncomment the line below to avoid errors when using Jupyter notebooks
# import nest_asyncio


def main(*, kafka_brokers: str, kafka_topic: str, country: str = 'mx',
         periods: int = 6, frequency_min: int = 10, start_timestamp_utc: str = '2018-01-01 00:00:00',
         parse_json_records: bool = True):

    s3 = boto3.client('s3')
    data_client = AwsDataClient(country, s3)
    start_datetime = datetime.strptime(start_timestamp_utc, '%Y-%m-%d %H:%M:%S')
    date_range = pd.date_range(start_datetime, periods=periods, freq=str(frequency_min)+'T')
    date_range_from_now = pd.date_range(datetime.now(), periods=periods, freq=str(frequency_min)+'T')

    if parse_json_records:
        producer = KafkaProducer(bootstrap_servers=kafka_brokers,
                                 value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    else:
        # Kafka Producer for plain messages
        producer = KafkaProducer(bootstrap_servers=kafka_brokers)

    for date_from_now, start_date in zip(date_range_from_now, date_range):
        # Uncomment the line below to avoid errors when using Jupyter notebooks
        # nest_asyncio.apply()
        end_date = start_date + timedelta(minutes=frequency_min)
        records = data_client.get_filtered_records(str(start_date), str(end_date))
        records_df = get_df_from_records(records)
        records_df['json'] = records_df.apply(lambda row: row.to_json(), axis=1)

        for index, record in records_df.iterrows():
            if parse_json_records:
                producer.send(kafka_topic, record['json'])
            else:
                producer.send(kafka_topic, bytes(record['json'], encoding='utf8'))

        print(f'Data ingested from: {str(start_date)} Until: {str(end_date)}')
        next_period = date_from_now + timedelta(minutes=frequency_min)
        pause.until(next_period)


if __name__ == '__main__':
    defopt.run(main)
