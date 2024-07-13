# Topic modeling preprocessing
import re
from datetime import datetime


def clean_text(x):
    x = str(x)
    for punct in "/-'":
        x = x.replace(punct, ' ')
    for punct in '&':
        x = x.replace(punct, f' {punct} ')
    for punct in '?!.,"#$%\'()*+-/:;<=>@[\\]^_`{|}~' + '“”’':
        x = x.replace(punct, '')
    x = re.sub('[0-9]{5,}', '#####', x)
    x = re.sub('[0-9]{4}', '####', x)
    x = re.sub('[0-9]{3}', '###', x)
    x = re.sub('[0-9]{2}', '##', x)
    return x


def sort_timestamps(texts, timestamps, days_length=14):
    timestamps_s = []
    for ts in timestamps:
        date_s = ts.split("T")[0].split("-")
        y, m, d = date_s[0], date_s[1], date_s[2]
        timestamps_s.append(f"{d}/{m}/{y}")

    datetime_objects = [datetime.strptime(ts, '%d/%m/%Y') for ts in timestamps_s]
    sorted_data = sorted(zip(texts, datetime_objects), key=lambda x: x[1])
    last_timestamp = sorted_data[-1][1]
    filtered_data = [(text, dt) for text, dt in sorted_data if (last_timestamp - dt).days <= days_length]
    filtered_texts, filtered_timestamps = zip(*filtered_data)
    return filtered_texts, filtered_timestamps
