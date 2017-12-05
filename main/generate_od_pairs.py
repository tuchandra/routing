import csv
import sys
import json
from random import random, randint
from math import floor

from geopy.distance import vincenty
from geopy.distance import great_circle
from shapely.geometry import shape, Point

ODPAIRS_PER_CITY = 10
OUTPUT_HEADER = ["ID", "origin_lon", "origin_lat", "destination_lon", "destination_lat", "straight_line_distance"]

def odpairs_from_grid_centroids(input_geojson_fn, output_csv_fn, min_dist, max_dist):
    """Randomly select origin-destination pairs from combinations of grid cells.

    Args:
        input_geojson_fn: geojson file containing gridcells
        output_csv_fn: path to output CSV file for od-pairs
        min_dist: only include od-pairs with a Euclidean distance greater than this threshold (km)
        max_dist: only include od-pairs with a Euclidean distance under this threshold (km)
    Returns:
        Void. Writes output origin-destination pairs along with straight-line distance to CSV file
    """

    with open(input_geojson_fn, 'r') as fin:
        gridcells = json.load(fin)['features']

    for feature in gridcells:
        feature['centroid'] = (shape(feature['geometry']).centroid.y, shape(feature['geometry']).centroid.x)
        feature['properties']['rid'] = str(feature['properties']['rid'])
        feature['properties']['cid'] = str(feature['properties']['cid'])

    print("{0} grid cells".format(len(gridcells)))
    routes_added = 0

    with open(output_csv_fn, 'w') as fout:
        csvwriter = csv.writer(fout)
        csvwriter.writerow(OUTPUT_HEADER)
        num_features = len(gridcells)
        dist_bins = [0] * max_dist

        while routes_added < ODPAIRS_PER_CITY:
            i = randint(0, num_features - 1)
            j = randint(0, num_features - 1)
            if i != j:
                # randomly determine which point will be origin and which destination
                feature1 = gridcells[i]
                feature2 = gridcells[j]

                dist_km = get_distance(feature1['centroid'], feature2['centroid'])

                # aim for ~same number of routes as I can query the APIs for
                if dist_km >= min_dist and dist_km <= max_dist:
                    dist_bins[floor(dist_km)] += 1
                    routes_added += 1

                    if routes_added % 500 == 0:
                        print("{0} routes added of {1}".format(routes_added, ODPAIRS_PER_CITY))

                    rowcolID = ";".join([feature1['properties']['rid'], feature1['properties']['cid'], feature2['properties']['rid'], feature2['properties']['cid']])
                    csvwriter.writerow([rowcolID, round(feature1['centroid'][1], 6), round(feature1['centroid'][0], 6), round(feature2['centroid'][1], 6), round(feature2['centroid'][0], 6), round(dist_km, 6)])

        for i in range(0, len(dist_bins)):
            print("{0} between {1} and {2} km in length.".format(dist_bins[i], i, i+1))


def get_distance(orig_pt, dest_pt):
    """Get distance in kilometers between two points."""

    try:
        # Vincenty = most accurate distance calculation
        return vincenty(orig_pt, dest_pt).kilometers
    except ValueError:
        # if Vincenty fails to converge, fall back on Great Circle -
        # less accurate but guaranteed
        return great_circle(orig_pt, dest_pt).kilometers


def main():
    min_dist = 0
    max_dist = 20  # distance in KM
    data_folder = "data"
    city = "chicago"

    odpairs_from_grid_centroids(input_geojson_fn = f"{data_folder}/{city}_grid.geojson",
                                output_csv_fn = f"{data_folder}/small_{city}_od_pairs.csv",
                                min_dist = min_dist,
                                max_dist = max_dist)


if __name__ == "__main__":
    main()