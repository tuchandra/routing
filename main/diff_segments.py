import ast
import copy
import csv
import os
import random
import sys

import geojson
from shapely.geometry import LineString

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = SCRIPT_DIR + "/data/"

def main():
    try:
        arg1 = sys.argv[1]
        arg2 = sys.argv[2]
    except IndexError as error:
        print("\nERROR: You need to provide two of:\ntraffic_gm, fastest_gm, traffic_gh, fastest_gh.\n")
        raise

    fnames = {
        "traffic_gm" : DATA_DIR + "chicago_routes_gmaps_traffic.csv",
        "fastest_gm" : DATA_DIR + "chicago_routes_gmaps_fastest.csv",
        "traffic_gh" : DATA_DIR + "chicago_routes_gh_traffic.csv",
        "fastest_gh" : DATA_DIR + "chicago_routes_gh_fastest.csv",
    }

    output_geojson = DATA_DIR + f"route_diffs_{arg1}_{arg2}.geojson"
    f1 = fnames[arg1]
    f2 = fnames[arg2]

    weighted_line(f1, f2, output_geojson)


def weighted_line(f1, f2, output_geojson):
    """Determine if there is a significant difference in where routes go.

    This function is long as shit, but here's what it does:
        1. Get all the polylines of the first set of routes
        2. Get all the polylines of the second set of routes
        3. Remove all routes that don't appear in both sets
        4. Combine route polylines together
        5. Turn set of route polylines into set of route segments
        6. Resample from segments and get the differences in the number
           of times each segment is used.
        7. Calculate significance of the resampled differences
        8. Store each segment and significance to a GeoJSON LineString
        9. Dump all the LineStrings to a file.

    What is the single responsibility principle, anyway?

    params
     - f1: str - filename of first routes CSV
     - f2: str - filename of second routes CSV
     - output_geojson: str - filename of output GeoJSON file

    return
     - None (write output to file instead)
    """

    print(f"Computing differences between routes for: \n\t{f1}\n\t{f2}")

    # Get polylines for first CSV
    # The polylines are stored as "[(lat1,lon1),(lat2,lon2),...,(latn, lonn)]"
    # so we can use the AST evaluator on them
    features1 = {}
    times1 = {}
    with open(f1, 'r') as fin:
        csvreader = csv.reader(fin)
        header = next(csvreader)

        id_idx = header.index("ID")
        time_idx = header.index("total_time_in_sec")
        polyline_idx = header.index("polyline_points")

        success1 = 0
        failure1 = 0

        for line in csvreader:
            try:
                route_id = line[id_idx]
                t_sec = float(line[time_idx])
                polyline = ast.literal_eval(line[polyline_idx])

                # Flip lat/lon to lon/lat per GeoJSON spec
                num_coordinates = len(polyline)
                for i in range(num_coordinates):
                    polyline[i] = (polyline[i][1], polyline[i][0])

                features1[route_id] = polyline
                times1[route_id] = t_sec
                success1 += 1
            except:
                failure1 += 1

    # Get polylines for second CSV
    # The polylines are stored as "[(lat1,lon1),(lat2,lon2),...,(latn, lonn)]"
    # so we can use the AST evaluator on them
    features2 = {}
    times2 = {}
    with open(f2, 'r') as fin:
        csvreader = csv.reader(fin)
        header = next(csvreader)

        id_idx = header.index("ID")
        time_idx = header.index("total_time_in_sec")
        polyline_idx = header.index("polyline_points")

        success2 = 0
        failure2 = 0

        for line in csvreader:
            try:
                route_id = line[id_idx]
                t_sec = float(line[time_idx])
                polyline = ast.literal_eval(line[polyline_idx])

                # Flip lat/lon to lon/lat per GeoJSON spec
                num_coordinates = len(polyline)
                for i in range(num_coordinates):
                    polyline[i] = (polyline[i][1], polyline[i][0])

                features2[route_id] = polyline
                times2[route_id] = t_sec
                success2 += 1
            except:
                failure2 += 1

    print(f"Found {len(features2)} routes for each type.")

    # Filter routes that don't appear in both CSVs
    # First: remove the ones that are in f1 but not in f2
    route_ids = list(features1.keys())
    for route_id in route_ids:
        if route_id in features2:  # it's okay, we have them both
            continue
        else:  # in f1 but not in f2; remove from f1
            del features1[route_id]
            del times1[route_id]

    # Next: remove the ones that are in f2 but not in f1
    route_ids = list(features2.keys())
    for route_id in route_ids:
        if route_id in features1:  # we good
            continue
        else:  # in f2 but not in f1, remove from f2
            del features2[route_id]
            del times2[route_id]

    # Combine polyline segments into dict of all possible route segments
    # TODO: maybe use douglas peucker
    all_segments = get_segments([features1, features2])
    print(f"Found {len(all_segments)} segments in total")

    # Resample route IDs
    iterations = 500
    route_ids = list(features1.keys())
    for i in range(iterations):
        sampled_ids = random.choices(route_ids, k = len(route_ids))  # as of 3.6
        segment_diffs = get_diffs(features1, features2, sampled_ids)

        for segment in all_segments:
            all_segments[segment].append(segment_diffs.get(segment, 0))

        if i % 10 == 9:
            print(f"Finished iteration {i+1} of {iterations}")


    # Calculate significance -- for each segment, look at the set of
    # differences between the two kinds of routes. If the set of differences
    # is strongly above or strongly below 0, we say it's significant.
    # 
    # At each step of this, we consider a particular segment (pt1, pt2). It
    # is a key into all_segments whose value is the list of differences
    # observed in resampling. We replace the list with the summary statistics
    # once they are computed.
    alpha = 0.01  # significance level
    for i, segment in enumerate(all_segments):
        sorted_segment_diffs = sorted(all_segments[segment])
        lower = sorted_segment_diffs[int(iterations * alpha / 2)]
        upper = sorted_segment_diffs[int(iterations * (1 - alpha) / 2)]
        median = sorted_segment_diffs[int(iterations / 2)]
        mean = sum(sorted_segment_diffs) / iterations

        significant = (lower > 0 and upper > 0) or (lower < 0 and upper < 0)
        all_segments[segment] = {'lower': lower, 'upper': upper,
                                 'median': median, 'significant':significant,
                                 'mean': mean}

        if i % 1000 == 999:
            print(f"Processed {i+1} out of {len(all_segments)}")

    # Code all of this as a GeoJSON!
    output = []
    for feature in all_segments:
        polyline = geojson.Feature(geometry = geojson.LineString(feature),
                        properties = {
                           'lower': all_segments[feature]['lower'],
                           'upper': all_segments[feature]['upper'],
                           'median': all_segments[feature]['median'],
                           'mean': all_segments[feature]['mean'],
                           'significant': all_segments[feature]['significant']
                        }
                   )

        output.append(polyline)

    fc = geojson.FeatureCollection(output)
    with open(output_geojson, 'w') as fout:
        geojson.dump(fc, fout)

    print(f"Dumped everything into a file")



def get_segments(dicts):
    """Combine dictionaries of routes into one dict of all route segments.

    params
     - dicts: List[Dict{str:List[(lon, lat)]}] -- dictionaries of routes

    return
     - Dict{(lon, lat) : List[int] }
    """

    all_segments = { }

    # go through each dict
    for routes in dicts:
        # in the dict, look at each route
        for route_id in routes.keys():
            # for each route, get each pair of points and
            # increment it
            for pt1, pt2 in zip(routes[route_id], routes[route_id][1:]):
                segment = (pt1, pt2)
                all_segments[segment] = []

    return all_segments


def get_diffs(routes1, routes2, route_ids):
    """Get difference in number of routes using each segment.

    params
     - routes1: Dict{str : List[(lon, lat)]} - first set of routes
     - routes2: Dict{str : List[(lon, lat)]} - second set of routes
     - route_ids: List[str] - IDs of routes to consider

    return
     - I have no idea
    """

    diffs = {}
    for routeid in route_ids:
        for pt1, pt2 in zip(routes1[routeid], routes1[routeid][1:]):
            segment = (pt1, pt2)
            diffs[segment] = diffs.get(segment, 0) + 1

        for pt1, pt2 in zip(routes2[routeid], routes2[routeid][1:]):
            segment = (pt1, pt2)
            diffs[segment] = diffs.get(segment, 0) - 1

    return diffs




if __name__ == "__main__":
    main()