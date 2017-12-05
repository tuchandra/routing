import os
import json
import argparse
from math import ceil, floor

from geojson import Polygon, Feature, FeatureCollection, dump
from shapely.geometry import shape, Point

"""
Code adapted from answer to question here:
http://gis.stackexchange.com/questions/54119/creating-square-grid-polygon-shapefile-with-python
"""

SCALE = 3

def grid(output_grid_fn, xmin, xmax, ymin, ymax, grid_height, grid_width, boundary):

    # check all floats
    xmin = float(xmin)
    xmax = float(xmax)
    ymin = float(ymin)
    ymax = float(ymax)
    grid_width = float(grid_width)
    grid_height = float(grid_height)

    # get rows, columns
    rows = ceil((ymax - ymin) / grid_height)
    cols = ceil((xmax - xmin) / grid_width)

    # create grid cells
    countcols = 0
    features = []
    while countcols < cols:
        # set x coordinate for this column
        grid_x_left = xmin + (countcols * grid_width)
        countcols += 1

        countrows = 0
        while countrows < rows:
            # update y coordinate for this row
            grid_y_bottom = ymin + (countrows * grid_height)
            countrows += 1

            # check if grid centroid contained in county boundary
            bottomleftcorner = (grid_x_left, grid_y_bottom)
            coords = [bottomleftcorner]

            # add other three corners of gridcell before closing grid with starting point again
            for i in [(0.001, 0), (0.001, 0.001), (0, 0.001), (0, 0)]:
                coords.append((bottomleftcorner[0] + i[1], bottomleftcorner[1] + i[0]))

            intersects = False
            for corner in coords[1:]:
                if boundary.contains(Point(corner)):
                    intersects = True
                    break

            if intersects:
                properties = {'rid': round(grid_y_bottom * 10**SCALE), 'cid': round(grid_x_left * 10**SCALE)}
                features.append(Feature(geometry=Polygon([coords]), properties=properties))

    with open(output_grid_fn, 'w') as fout:
        dump(FeatureCollection(features), fout)

def main():
    """Generate grid for a GeoJSON json file passed on the command line.

    Chicago data from https://whosonfirst.mapzen.com/spelunker/id/85940195
    Repurpose for other cities as appropriate -- it should probably work.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("features_geojson", help="Path to GeoJSON with features to be gridded.")
    parser.add_argument("output_folder", help="Folder to contain output grid GeoJSONs.")
    args = parser.parse_args()

    with open(args.features_geojson, 'r', encoding = 'utf8') as fin:
        feature = json.load(fin)

    boundary = shape(feature["geometry"])
    bb = feature["bbox"]

    # OPTIONAL -- simplify boundary using shapely's implementation of Douglas-
    # Peucker algorithm. This was untested but it should work; first argument
    # is the tolerance parameter (for which I provided an arbitrary value). Use
    # this if the script is taking too long to run (the grid function does
    # many expensive point-in-polygon computations)
    # boundary.simplify(0.00001)

    xmin = bb[0]  # most western point
    xmax = bb[2]  # most eastern point
    ymin = bb[1]  # most southern point
    ymax = bb[3]  # most northern point

    grid_height = 0.001
    grid_width = 0.001
    xmin = floor(xmin * 10**SCALE) / 10**SCALE
    ymax = ceil(ymax * 10**SCALE) / 10**SCALE

    grid("{0}_grid.geojson".format(os.path.join(args.output_folder, args.features_geojson)),
         xmin, xmax, ymin, ymax, grid_height, grid_width, boundary)


if __name__ == "__main__":
    main()