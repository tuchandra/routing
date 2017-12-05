import csv
import json
import os

import requests


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

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


def parse_poly1():
    """Read the data from poly1.txt and return segment : lat/lon info.

    params
     - None, but expects file data/poly1.txt to exist

    return
     - geo: Dict[int : List[pair]], where pair = {"x": float, "y": float},
       and the int key is the segment ID
    """

    geo = {
        # int : List[{'x': float, 'y': float}]
    }

    poly1_fname = SCRIPT_DIR + "/data/poly1.txt"
    with open(poly1_fname) as poly1:
        assert next(poly1).strip() == "["
        assert next(poly1).strip() == "{"

        # Line format:
        # 111:[[{x:-87.aa,y:41.bb}, {x:-87.cc,y:41.dd}, ...]],
        # so line.strip().split(":")[0] gives the segment ID,
        # and everything after is the rest of the line.
        for line in poly1:
            # Last line
            if line.strip() == "}":
                break

            line = line.strip().split(":")
            segment_id = int(line[0])
            rest = ":".join(line[1:])

            # Remove possible trailing comma -- always there except last line
            if rest[-1] == ",":
                rest = rest[:-1]

            # Convert to proper JSON by quoting keys x and y
            rest = rest.replace('x', '"x"').replace('y', '"y"')
            rest = json.loads(rest)
            coords = rest[0]  # list of pairs

            geo[segment_id] = coords

    return geo


if __name__ == "__main__":
    # Get all traffic data
    segments = {
        # color: List[int]
    }
    for color in ['green', 'yellow', 'red']:
        ...#segments[color] = get_data(color)

    # Read data downloaded from City of Chicago traffic tracker website
    # and parse into a dictionary -- stored in poly1.txt, which is
    # extremely messy.
    #
    # TODO: put in README where poly1 came from. poly2 and
    # poly4 are empty. poly3 is I think the regions.
    geo = parse_poly1()
