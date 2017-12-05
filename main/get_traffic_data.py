import csv
import json

import requests

def get_data(color):
    """Get traffic data for low- / medium- / high-traffic segments.

    Make request to get traffic data, parse output, and return list of
    road segments from that data.

    params
     - color: str - either 'green', 'yellow', or 'red' for low-, medium-
       or high-traffic. This determines the request to execute

    return
     - segments: List[int] - list of segment IDs that have that type of
       traffic.
    """
    
    # Set request URL
    base = "http://webapps1.cityofchicago.org/traffic/"
    url_parm = ""
    if color == "green":
        url_param = "sra"
    elif color == "yellow":
        url_param = "sra_yellow"
    elif color == "red":
        url_param = "sra_red"
    else:
        print("Invalid parameter color; must be 'green', 'yellow', 'red'.")
        return

    url = base + url_param + ".jsp"
    r = requests.get(url)
    response = r.json()

    # Expected format:
    # { "sra_red" :  (or sra_yellow or sra_green)
    #   [
    #     { "segmentid" : "111" },
    #     { "segmentid" : "222" },
    #     ...
    #   ]
    # }
    # 

    response_values = response["sra_" + color]
    segments = map(lambda value: int(value["segmentid"]), response_values)
    segments = list(segments)

    return segments



if __name__ == "__main__":
    # Get all traffic data
    segments = {
        # color: List[int]
    }
    for color in ['green', 'yellow', 'red']:
        ...#segments[color] = get_data(color)

    # Read data downloaded from City of Chicago traffic tracker website
    # and parse into a dictionary -- stored in poly1.txt and poly3.txt,
    # which annoyingly have different formats. Oh well, data science is a
    # lot about cleaning.
    #