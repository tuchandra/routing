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


def write_to_csv(all_segments, geo, out_fn):
    """Write traffic information to a CSV file.

    Output format is [segment_id, color, origin_lon, origin_lat,
    dest_lon, dest_lat]. Color is one of 'red', 'yellow', 'green'.

    Where the road segment is a polyline (i.e., length of list is more
    than 2), we code each line as its own row in the CSV.

    e.g., if the road is ({x:1, y:2}, {x:3, y:4}, {x:5, y:6})
    then the CSV has two rows for this road, one from (1,2) --> (3,4)
    and another from (3,4) --> (5,6).

    params
     - all_segments: Dict[str : List[int]] - strings are red/yellow/green,
       values are list of segment IDs that have that type of traffic.
     - geo: Dict[int : List[pair]], with pair = {"x": float,"y": float},
       and the int key is the segment ID
     - out_fn: str - output file name

    return
     - none, but writes data to CSV
    """

    output_header = ["segment_id", "color", "origin_lon",
                     "origin_lat", "dest_lon", "dest_lat"]

    segments_written = 0
    with open(out_fn, 'w') as fout:
        csvwriter = csv.writer(fout)
        csvwriter.writerow(output_header)

        for color in ['green', 'yellow', 'red']:
            segments = all_segments[color]
            for segment_id in segments:
                # polyline is a list of coordinates, {x:___, y:___}.
                # we want to encode each pair of coordinates as its
                # own row in the CSV.
                polyline = geo[segment_id]
                for origin, dest in zip(polyline, polyline[1:]):
                    origin_lon = origin['x']
                    origin_lat = origin['y']
                    dest_lon = dest['x']
                    dest_lat = dest['y']

                    row = [segment_id, color, origin_lon, origin_lat,
                           dest_lon, dest_lat]
                    csvwriter.writerow(row)

                    segments_written += 1
                    if segments_written % 100 == 0:
                        print(f"Added {segments_written} roads so far.")

            print(f"Added all {color} roads.")

if __name__ == "__main__":
    # Get all traffic data
    all_segments = {
        # color: List[int]
    }
    for color in ['green', 'yellow', 'red']:
        all_segments[color] = get_data(color)

    # Read data downloaded from City of Chicago traffic tracker website.
    # Stored in poly1.txt, which is extremely messy.
    #
    # TODO: put in README where poly1 came from. poly2 and
    # poly4 are empty. poly3 is I think the regions.
    geo = parse_poly1()

    # Dump to CSV
    out_fn = SCRIPT_DIR + "/data/traffic.csv"
    write_to_csv(all_segments, geo, out_fn)

