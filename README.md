CynoMap
=======

A simple library to take a EVE API Corp Members output and work out the jump range between them, so for example, a cyno corp, you can work out all the jump routes available within the corporation.

This is extremely experimental is nowhere complete. The maps are generated out in SVG format and a simple Flask container is included to allow maps to be generated as required for a specific lightyear distance.

LICENSE
-------

This work is licensed under the BSD 3 Clause License, please consult the LICENSE file for further details.

Requirements
------------

* Entity's EVE API module (pip install eveapi).
* Latest SDE extract from CCP in Sqlite format.

How It Works
------------

1. Extract all systems (excluding wormholes) from the EVE SDE.
2. Extract all gate jumps from the EVE SDE.
3. Call the MemberTracking EVE API endpoint with the supplied API keys.
4. For each member, check their location and work out their true System location ID if they're in a station
5. For each Member, check the distance to another member, if its below the lightyear limit, store it as a route
6. Render the systems in SVG
7. Render the gate jumps in the SVG
8. Render the cyno routes in the SVG

Distance calculation is based on CCP's lightyear being 9460000000000000 meters, instead of the actual value of 9460730472580800 meters. The `calc_distance` function contains the actual distance calcuation function and will work with any dict of x/y/z coordinates.

Rendering on a decent system takes in the region of 1-2 seconds, depending on network delay for the API calls. The biggest delay is usually incurred by browsers parsing and rendering the supplied SVG due to the number of elements.

Using The Library
-----------------

`cynomap` contains a single object `CynoMap` which has properties to pull out most of the data used in the generation of the map, the single `avg` property will render the map and cache the output.

As this was a proof of concept, its highly recommended that you modify the codeto suite your needs, instead of trying to use the existing, quirky interface.


Note About Map Orientation
--------------------------

It maybe due to SDE issues, but the 2d representation of the EVE universe we all know is actually the X/Z coordinates, not X/Y. Worth nothing when you're looking through the code and see a lot of references to X/Z.
