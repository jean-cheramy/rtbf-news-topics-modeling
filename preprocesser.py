import re
from datetime import datetime


def clean_text(x: str) -> str:
    """
    Cleans the input text by removing punctuation, special characters,
    and replacing digits with placeholders.

    Args:
    - x (str): Input text to be cleaned.

    Returns:
    - str: Cleaned text.
    """
    x = str(x)
    # Replace specific punctuations with spaces
    for punct in "/-’' ":
        x = x.replace(punct, ' ')
    # Surround certain punctuations with spaces
    for punct in '&':
        x = x.replace(punct, f' {punct} ')
    # Remove other punctuations and special characters
    for punct in '"#$%*+-/:<=>@[\\]^_`{|}~' + '“”':
        x = x.replace(punct, '')
    # Replace digits with placeholders
    x = re.sub('[0-9]{5,}', '#####', x)
    x = re.sub('[0-9]{4}', '####', x)
    x = re.sub('[0-9]{3}', '###', x)
    x = re.sub('[0-9]{2}', '##', x)
    return x


def sort_timestamps(texts: list, timestamps: list, days_length: int = 90) -> (list, list):
    """
    Sorts and filters texts based on timestamps within a specified time window.

    Args:
    - texts (list): List of texts to be sorted.
    - timestamps (list): List of timestamp strings.
    - days_length (int): Number of days of data to consider.

    Returns:
    - filtered_texts (list): Sorted and filtered list of texts.
    - filtered_timestamps (list): Corresponding timestamps after filtering.
    """
    # Format timestamps to 'dd/mm/yyyy' and convert to datetime objects
    timestamps_s = []
    for ts in timestamps:
        date_s = ts.split("T")[0].split("-")
        y, m, d = date_s[0], date_s[1], date_s[2]
        timestamps_s.append(f"{d}/{m}/{y}")
    datetime_objects = [datetime.strptime(ts, '%d/%m/%Y') for ts in timestamps_s]
    sorted_data = sorted(zip(texts, datetime_objects), key=lambda x: x[1])
    last_timestamp = sorted_data[-1][1]
    # Filter texts based on the specified days_length
    filtered_data = [(text, dt) for text, dt in sorted_data if (last_timestamp - dt).days <= days_length]
    filtered_texts, filtered_timestamps = zip(*filtered_data)
    return filtered_texts, filtered_timestamps
