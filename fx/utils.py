import pytz
import datetime as dt


def date_to_iso(date):
    date = pytz.utc.localize(date).astimezone(pytz.utc)
    date = date - dt.timedelta(hours=9)
    return dt.datetime.strftime(date, "%Y-%m-%dT%H:%M:%S.%f000Z")


def iso_to_date(iso):
    date = dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%f000Z")
    date = pytz.utc.localize(date).astimezone(pytz.timezone("Asia/Tokyo"))
    return date


def date_to_str(date):
    return date.strftime("%Y-%m-%d %H:%M:%S")
