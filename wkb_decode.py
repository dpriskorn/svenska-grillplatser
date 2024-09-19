from shapely import wkb
from pyproj import Transformer

def convert_wkb_to_wgs84(wkb_hex):
    # Decode the WKB string to get the point geometry
    point = wkb.loads(bytes.fromhex(wkb_hex))

    # Extract the coordinates (SWEREF 99 TM)
    x_sweref99, y_sweref99 = point.x, point.y

    # Create a transformer object to convert from SWEREF 99 TM (EPSG:3006) to WGS 84 (EPSG:4326)
    transformer = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True)

    # Convert to WGS 84 (longitude, latitude)
    longitude, latitude = transformer.transform(x_sweref99, y_sweref99)

    return latitude, longitude

# Example 1 WKB string in hexadecimal format
wkb_hex = "01010000A0C00B0000E038C0B233740541DC9FE370007F57410000000000000000"

# Convert and print the coordinates
latitude, longitude = convert_wkb_to_wgs84(wkb_hex)
print(f"{latitude}, "
      f"{longitude}")
# -> according to OSM this is a point in Middelfart County in Denmark, see
# https://www.openstreetmap.org/search?query=55.47261267664004%2C%209.868184979862724#map=17/55.472613/9.868185&layers=N

# Example 2 WKB string in hexadecimal format
wkb_hex = "01010000A0C00B00001AFA49EB086A05416ABFEEA8F87E574100007AA825305340"

# Convert and print the coordinates
latitude, longitude = convert_wkb_to_wgs84(wkb_hex)
print(f"{latitude}, "
      f"{longitude}")
# -> according to OSM this is a point in Denmark also