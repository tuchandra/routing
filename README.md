# routing
Algorithmically auditing Google Maps routes produced during heavy traffic in the City of Chicago.

<img src="https://github.com/tuchandra/routing/blob/master/images/gmaps-with-legend.png?raw=true" width="300" height="600">

## Overview
This is a research project to algorithmically audit Google Maps in heavy Chicago traffic. We compare the routes obtained from Google Maps to routes created with an open-source routing library, GraphHopper, using live traffic data from the City of Chicago. We use a [custom fork of GraphHopper](https://github.com/tuchandra/graphhopper), but the [original repo](https://github.com/graphhopper/graphhopper/) will of course be most up-to-date.

## Included Files
These files are based off Isaac Johnson's work in his [route-externalities](https://github.com/joh12041/route-externalities/) repository.

`grid_creation.py <input GeoJSON file> <output folder>` - this takes a GeoJSON file representing a city (we use Chicago) and creates a square grid for the city. Takes as arguments the aforementioned GeoJSON file and an output folder. This is the only file that takes command line inputs, but we include the GeoJSON file used in `main/data/chicago_boundary.geojson`

`generate_od_pairs.py` - takes the grids from above and generates origin-destination pairs (OD pairs).

`get_routes.py` - get the routes from the Google Maps API. Originally designed to handle both Google Maps and Mapquest, but repurposed here for Google Maps alone, the design of this script could be simplified. This requires an API key to exist in the location `api_keys/google.txt`.

`get_traffic_data.py` - read live traffic data from the City of Chicago. This uses `main/data/poly1.txt`, which may be out of date since the time of writing (it's a gigantic variable lifted from the source code of their traffic tracker).

`diff_segments.py` - compute differences between all the sets of routes generated

`plotting.ipynb` - create some graphs (others were created in QGIS)

See [my GraphHopper repo](https://github.com/tuchandra/graphhopper) as well for more information.