import csv
import os


EXPECTED_HEADER = ["ID", "name", "polyline_points", "total_time_in_sec",
                   "total_distance_in_meters", "number_of_steps",
                   "maneuvers", "beauty", "simplicity", "pctNonHighwayTime",
                   "pctNonHighwayDist", "pctNeiTime", "pctNeiDist"]

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = SCRIPT_DIR + "/data/"

def main():
    # Set up file paths
    optimization = "fastest"  # "fastest" or "traffic"
    gmaps_csv = DATA_DIR + f"chicago_routes_gmaps_{optimization}_matched.csv"
    gh_csv = DATA_DIR + f"chicago_routes_gh_{optimization}.csv"
    output_csv = DATA_DIR + f"chicago_routes_{optimization}_merged.csv"

    threshold = 0.10  # error tolerance between distance results

    print(f"\nMerging {gmaps_csv} and {gh_csv} with {threshold} threshold " +
          f"and output to {output_csv}.")

    # Configure indices for expected header
    route_idx = EXPECTED_HEADER.index("ID")
    dist_idx = EXPECTED_HEADER.index("total_distance_in_meters")
    beauty_idx = EXPECTED_HEADER.index("beauty")
    simplicity_idx = EXPECTED_HEADER.index("simplicity")
    nhwdist_idx = EXPECTED_HEADER.index("pctNonHighwayDist")
    nhwtime_idx = EXPECTED_HEADER.index("pctNonHighwayTime")
    sntime_idx = EXPECTED_HEADER.index("pctNeiTime")
    sndist_idx = EXPECTED_HEADER.index("pctNeiDist")

    gh_data = {}
    with open(gh_csv, 'r') as fin:
        csvreader = csv.reader(fin)
        gh_header = next(csvreader)
        assert gh_header == EXPECTED_HEADER[:len(gh_header)]

        for line in csvreader:
            if not line: continue  # because Windows

            try:
                route_id = line[route_idx]
                dist = float(line[dist_idx])
                beauty = float(line[beauty_idx])
                simplicity = float(line[simplicity_idx])
                non_hw_time = float(line[nhwtime_idx])
                non_hw_dist = float(line[nhwdist_idx])
                sn_time = float(line[sntime_idx])
                sn_dist = float(line[sndist_idx])
                gh_data[route_id] = {'dist':dist, 'beauty':beauty, 'simplicity':simplicity, 'non_hw_time':non_hw_time,
                                     'non_hw_dist':non_hw_dist, 'sn_time':sn_time, 'sn_dist':sn_dist}
            except ValueError:
                print("GH:", line)

    with open(gmaps_csv, 'r') as fin:
        csvreader = csv.reader(fin)
        api_header = next(csvreader)
        assert api_header == EXPECTED_HEADER[:len(api_header)]

        processed = 0
        skipped = 0
        kept = 0
        with open(output_csv, 'w') as fout:
            csvwriter = csv.writer(fout)
            csvwriter.writerow(EXPECTED_HEADER)

            for line in csvreader:
                if not line: continue  # because Windows

                route_id = line[route_idx]
                dist = float(line[dist_idx])

                try:
                    if route_id not in gh_data:
                        skipped += 1
                        continue

                    if route_id in gh_data and abs((dist - gh_data[route_id]['dist']) / dist) < threshold:
                        line.extend([gh_data[route_id]['beauty'], gh_data[route_id]['simplicity'],
                                     gh_data[route_id]['non_hw_time'], gh_data[route_id]['non_hw_dist'],
                                     gh_data[route_id]['sn_time'], gh_data[route_id]['sn_dist']])
                        csvwriter.writerow(line)
                        kept += 1

                    processed += 1
                except ValueError:
                    print("API:", line)

    print(f"{processed} external API routes processed, {skipped} skipped, " +
          f"and {kept} kept.")


if __name__ == "__main__":
    main()
