from cleaner_api.data_cleaning_api import clean_df

import pandas as pd

df = pd.read_csv("sample_dataset.csv")

to_datetime = ('order_creation_date', 'event_created_date', 'event_start_date', 'event_end_date')
for col in to_datetime:
    df[col] = pd.to_datetime(df[col], format="%d/%m/%y")

df = clean_df(df)
df.to_csv('output_dataset.csv', index=False)
