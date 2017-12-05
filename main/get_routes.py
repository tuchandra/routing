#!/usr/bin/env python

"""Get routes from Google Maps APIs.

Requires API keys as well as input origin-destination pairs.
"""

from abc import ABCMeta, abstractmethod

import csv
import argparse
import time
import json
import ast
import traceback
import urllib.parse
import urllib.request
import argparse
import datetime

from random import random
from time import strftime

import googlemaps

class API(object, metaclass = ABCMeta):

    def __init__(self, api_key_fn, api_limit=2500, stop_at_api_limit=True, output_num=1):
        with open(api_key_fn, 'r') as keyfile:
            self.api_key = next(keyfile).strip()
        self.api_limit = api_limit
        self.stop_at_api_limit = stop_at_api_limit
        if output_num > 1:
            self.get_alternatives = True
        else:
            self.get_alternatives = False
        self.output_num = output_num
        self.logfile_fn = "logs/chicago_grid_PLATFORM_log.txt"
        self.queries_made = 0
        self.exceptions = 0

    @classmethod
    @abstractmethod
    def get_routes(self, origin, destination, route_id):
        self.queries_made += 1
        return [Route()]

    def write_to_log(self, mess_type="LOG", message=""):
        with open(self.logfile_fn, 'a') as fout:
            fout.write("[{0}] At {1}: {2}. {3} queries made.\n".format(mess_type, strftime("%Y-%m-%d %H:%M:%S"), message, self.queries_made))

    def end(self):
        self.write_to_log("END", "Ending script")

    def reset(self):
        self.queries_made = 0
        self.exceptions = 0
        self.write_to_log("RESET", "Returned counts to zero")


class Route(dict):

    def __init__(self, route_id = "", name = "", route_points = [],
                 time_sec = None, distance_meters = None, maneuvers = []):
        self['ID'] = route_id
        self['name'] = name
        self['polyline_points'] = route_points
        self['total_time_in_sec'] = time_sec
        self['total_distance_in_meters'] = distance_meters
        self['maneuvers'] = maneuvers
        self['number_of_steps'] = len(maneuvers)
        

class GoogleAPI(API):

    def __init__(self, api_key_fn, api_limit = 2500, stop_at_api_limit = True, output_num = 1):
        super().__init__(api_key_fn, api_limit, stop_at_api_limit, output_num)
        self.logfile_fn = self.logfile_fn.replace("PLATFORM", "google")
        self.write_to_log("START", "Starting Google API")
        self.client = None

    def get_routes(self, origin, destination, route_id):
        if not self.client:
            self.connect_to_api()

        routes = []
        try:
            route_jsons = self.client.directions(
                origin = origin,
                destination = destination,
                units = "metric",
                mode = "driving",
                departure_time = "now",
                alternatives = self.get_alternatives
            )

        except Exception:
            traceback.print_exc()
            self.exceptions += 1
            self.write_to_log("EXCEPTION", "Connection failed")
            return [Route()]
                        
        try:
            idx = 0
            for route_json in route_jsons:
                # no waypoints - take first leg, which is entire trip
                route = route_json.get('legs')[0]

                # overview_polyline would provide smoothed overall line
                # overviewPolylinePoints = route_json.get('overview_polyline').get('points')
                # instead, we take the least-smoothed version at the step-level
                route_steps = route.get('steps')
                route_points = []
                for step in route_steps:
                    polyline_str = step.get("polyline", {"points":""}).get("points")
                    polyline_pts = self.decode(polyline_str)
                    # check if first point duplicates last point from previous step
                    if polyline_pts and route_points and polyline_pts[0] == route_points[-1]:
                        polyline_pts.pop(0)
                    route_points.extend(polyline_pts)

                total_time_sec = route.get('duration').get('value')
                total_distance_meters = route.get('distance').get('value')

                maneuvers = list()
                for i in range(0, len(route_steps)):
                    if 'maneuver' in route_steps[i]:
                        maneuvers.append(route_steps[i].get('maneuver'))

                name = "main"
                if idx > 0:
                    name = "alternative {0}".format(idx)

                routes.append(Route(route_id = route_id, name = name,
                    route_points = route_points, time_sec = total_time_sec,
                    distance_meters = total_distance_meters, maneuvers = maneuvers))

                idx += 1

        except Exception:
            traceback.print_exc()
            self.exceptions += 1
            try:
                self.write_to_log("EXCEPTION", str(route_json))
            except Exception:
                traceback.print_exc()
                self.write_to_log("EXCEPTION", "Route processing failed. JSON not valid")
            return [Route()]

        self.queries_made += 1
        return routes
        
    
    def connect_to_api(self):
        # ValueError if invalid API-Key
        self.client = googlemaps.Client(key=self.api_key)


    def decode(self, point_str):
        '''Decodes a polyline that has been encoded using Google's algorithm
        http://code.google.com/apis/maps/documentation/polylinealgorithm.html

        This is a generic method that returns a list of (latitude, longitude)
        tuples.

        Code taken from: https://gist.github.com/signed0/2031157

        :param point_str: Encoded polyline string.
        :type point_str: string
        :returns: List of 2-tuples where each tuple is (latitude, longitude)
        :rtype: list

        '''

        # sone coordinate offset is represented by 4 to 5 binary chunks
        coord_chunks = [[]]
        for char in point_str:

            # convert each character to decimal from ascii
            value = ord(char) - 63

            # values that have a chunk following have an extra 1 on the left
            split_after = not (value & 0x20)
            value &= 0x1F

            coord_chunks[-1].append(value)

            if split_after:
                coord_chunks.append([])

        del coord_chunks[-1]

        coords = []

        for coord_chunk in coord_chunks:
            coord = 0

            for i, chunk in enumerate(coord_chunk):
                coord |= chunk << (i * 5)

            #there is a 1 on the right if the coord is negative
            if coord & 0x1:
                coord = ~coord #invert
            coord >>= 1
            coord /= 100000.0

            coords.append(coord)

        # convert the 1 dimensional list to a 2 dimensional list and offsets to
        # actual values
        points = []
        prev_x = 0
        prev_y = 0
        for i in range(0, len(coords) - 1, 2):
            if coords[i] == 0 and coords[i + 1] == 0:
                continue

            prev_x += coords[i + 1]
            prev_y += coords[i]
            # a round to 6 digits ensures that the floats are the same as when
            # they were encoded
            points.append((round(prev_y, 6), round(prev_x, 6)))

        return points


def main():
#    parser = argparse.ArgumentParser()
#    parser.add_argument("start_time", type=int, help="## between 00 and 24")
#    args = parser.parse_args()
#
#    # Sleep if the start_time is in the future
    current_time = datetime.datetime.now()
    # start_time = datetime.datetime(year = current_time.year, month = current_time.month, day = current_time.day, hour = args.start_time)
    start_time = current_time
    sleep_for = (start_time - current_time).seconds
    print("Will sleep for {0} seconds before starting.".format(sleep_for))

    input_odpairs_fn = "data/chicago_od_pairs.csv"
    output_routes_g_fn = "data/chicago_google_routes.csv"

    # Read all origin/destination pairs from CSV into list
    od_pairs = []
    with open(input_odpairs_fn, 'r') as fin:
        # open file with origin long, origin lat, dest long, dest lat
        csvreader = csv.reader(fin)
        input_header = ["ID", "origin_lon", "origin_lat", "destination_lon",
                        "destination_lat", "straight_line_distance"]
        assert next(csvreader) == input_header

        id_idx = input_header.index("ID")
        oln_idx = input_header.index("origin_lon")
        olt_idx = input_header.index("origin_lat")
        dln_idx = input_header.index("destination_lon")
        dlt_idx = input_header.index("destination_lat")
        dist_idx = input_header.index("straight_line_distance")

        for row in csvreader:
            if not row:  # every other row is empty, because Windows
                continue

            origin = float(row[olt_idx]), float(row[oln_idx])
            destination = float(row[dlt_idx]), float(row[dln_idx])
            route_id = row[id_idx]
            od_pairs.append({
                'id' : route_id,
                'origin' : origin,
                'destination' : destination
            })  # this style is very javascript

    # Do routing requests for each o/d pair
    with open(output_routes_g_fn, 'w') as foutg:
        fieldnames = ['ID', 'name', 'polyline_points', 'total_time_in_sec',
                      'total_distance_in_meters', 'number_of_steps', 'maneuvers']
        csvwriter_g = csv.DictWriter(foutg, fieldnames=fieldnames)
        csvwriter_g.writeheader()
        g = GoogleAPI(api_key_fn = "api_keys/google.txt", api_limit = 2400, 
                      stop_at_api_limit = True, output_num = 2)
        
        time.sleep(sleep_for)
        g.write_to_log("LOG", "Starting script.")

        for od_pair in od_pairs:
            try:
                routes_g = g.get_routes(od_pair['origin'], od_pair['destination'], od_pair['id'])
                for route in routes_g:
                    csvwriter_g.writerow(route)

                if (g.exceptions + 1) % 40 == 0:
                    g.write_to_log("TOO MANY EXCEPTIONS", "{0} exceptions reached. Should be halting script".format((g.exceptions, m.exceptions)))
                    #break

                if g.queries_made % 100 == 0:
                    g.write_to_log("LOG", "Every 100 query check")

                # when almost hit API limit, shut-down
                if g.stop_at_api_limit and g.queries_made == g.api_limit:
                    current_time = datetime.datetime.now()
                    sleep_for = (start_time - current_time).seconds
                    g.write_to_log("API LIMIT", "Script sleeping for {0} seconds. Current route ID is {1}".format(sleep_for, od_pair['id']))
                        
                    time.sleep(sleep_for)
                    g.reset()
                else:
                    # be nice to API
                    time.sleep(1 + (0.5 - random()))

            except KeyboardInterrupt:
                traceback.print_exc()
                break

        g.end()

if __name__ == "__main__":
    main()
