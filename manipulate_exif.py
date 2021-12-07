# Created By  : G. Wilson
# Company : Southern Company Services, Inc.
# version : 1.0

'''
This is a script to obfuscate the GIS locations of a set of images in a directory
Python package requirenments-
Python version 3.6.13
exifread==2.3.2
gpsphoto==2.2.3
piexif==1.1.3
pillow==8.4.0
pyproj==2.6.1.post1
simplekml==1.3.6

Make sure you install EXIFtool from here - https://exiftool.org/

Credits :
-https://ocefpaf.github.io/python4oceanographers/blog/2013/12/16/utm/
-https://www.mkompf.com/trekka/geoposition.php
-https://simplekml.readthedocs.io/

This script works as follows:
-Generate a random x scaler
-Generate a random y scaler
-Read all files in a directory (Read below on how to structure the directory)
-Process the exif information
-Determine UTM zone (s) -- if multiple, raise a warning...
-Convert exif GPS locations to UTM
-Scale all locations by the scaler values
-Convert UTM values to WGS84
-Write new locations to EXIF of the files
-Add flags for stripping all non-location data from the files

If you want to know more about UTM, visit: https://www.maptools.com/tutorials/grid_zone_details
Cool site for coordinate checking: https://www.mkompf.com/trekka/geoposition.php
exifTool https://exiftool.org
'''

import os
from random import random, uniform, sample
from GPSPhoto import gpsphoto
from pyproj import Proj
import utm
from typing import cast
import simplekml
import subprocess

# initialize global variables
scaler_x = 0
scaler_y = 0
images = {}
path_images = r'images/source'
path_output = r'images/output'


class GeoImage:
    has_georeference = False
    lat = 0
    lon = 0
    x = 0
    y = 0
    zone = None
    zone_letter = None
    path = None
    name = ""
    height = 0

    def __init__(self, path):
        self.path = path
        data = gpsphoto.getGPSData(path)
        if "Latitude" in data.keys() and "Longitude" in data.keys():
            lat, lon = (data["Latitude"], data["Longitude"])
            if "Altitude" in data.keys():
                self.height = data['Altitude']
            z, l, x, y = utm.project((lon, lat))
            self.lat = lat
            self.lon = lon
            self.zone = z
            self.zone_letter = l
            self.x = x
            self.y = y
            self.has_georeference = True


def generate_scalers():
    global scaler_x, scaler_y
    scaler_x = uniform(-1, 1)
    scaler_y = uniform(-1, 1)


def load_images():
    path_source = path_images
    num_files = 0
    num_georeferenced = 0
    with os.scandir(path_source) as entries:
        for entry in entries:
            if entry.is_file:
                num_files += 1
                path_abs = os.path.join(os.curdir, entry)
                image = GeoImage(path_abs)
                image.name = os.path.basename(entry)
                images[image.path] = image
                if (image.has_georeference):
                    num_georeferenced += 1
    print(f'Processed {num_files}, with {num_georeferenced} having GPS data.')


def process_scaling():
    # check to see if all images are in the same zone
    zone = None
    zone_letter = None
    zone_conflict = False
    x_min = None
    x_max = 0
    y_min = None
    y_max = 0
    alt_min = None
    for key in images.keys():
        img = cast(GeoImage, images[key])
        if img.has_georeference:
            if alt_min is None:
                alt_min = img.height
            if x_min is None:
                x_min = img.x
            if y_min is None:
                y_min = img.y
            if img.height < alt_min:
                alt_min = img.height
            if img.x < x_min:
                x_min = img.x
            if img.y < y_min:
                y_min = img.y
            if img.x > x_max:
                x_max = img.x
            if img.y > y_max:
                y_max = img.y
        if zone is None:
            zone = img.zone
            zone_letter = img.zone_letter
        else:
            zone_conflict = img.zone != zone or img.zone_letter != zone_letter
    if zone_conflict:
        print("Zone Conflict Detected")
        return False
    else:
        print("No Zone Conflicts Detected")
        print(f"X Limits: {x_min}, {x_max}")
        print(f"Y Limits: {y_min}, {y_max}")
        # if we have no min at this point, none of the images were geocoded. Only proceed if we have all values
        if x_min is not None and y_min is not None and alt_min is not None:
            # We need to randomly select a zone to push the coordinates we're about to shift to.
            # For fun, we'll limit the target zones to those in the Atlantic Ocean
            zone_letters = ["R", "S", "T", "U"]
            zone_letter = sample(zone_letters, 1)  # Pick a random letter from the list
            zones = [19, 20, 21, 22, 23, 24, 25, 26, 27]
            zone = sample(zones, 1)  # Pick a random zone from the list

            # Now we'll do a quick shift of coordinates to move the minimum x to 500,000
            # This is the center of the UTM zone.
            x_adder = 500000 - x_min
            # Now we'll scale the adder with our x scaler.
            x_adder = round(x_adder * scaler_x)

            # Now we'll calculate a random adder for the y side and scale it.
            # At the time I'm writing this, I don't know how to properly calculate the center y coordinate
            # of a specified UTM zone.  When I figure this out, I'll modify it to operate similarly to the x axis.
            y_adder = round(1000 * scaler_y)

            # Now we'll shift the coordinates by the adders
            for key in images.keys():
                img = cast(GeoImage, images[key])
                if img.has_georeference:
                    img.x += x_adder
                    img.y += y_adder
                    # shift height to a base of sea level
                    img.height = round(img.height - alt_min, 3)
                    # Now we've got coordinates that are shifted from their original position.
                    # Now, we can re-project UTM into WGS84 lat, lon coordinates.
                    myProj = Proj(f"+proj=utm +zone={zone[0]}{zone_letter[0]}, +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
                    img.lon, img.lat = myProj(img.x, img.y, inverse=True)
        return True


def generate_kml():
    kml = simplekml.Kml()
    kml.document.name = "TempKML"
    for key in images.keys():
        img = cast(GeoImage, images[key])
        if img.has_georeference:
            pnt = kml.newpoint(name=img.name, description="randomly moved file",
                               coords=[(img.lon, img.lat, img.height)])
    kml.save(path="tmpkml.kml")


def saveNewFiles():
    # remove GPS location information (EXIF) data from the images
    # remove XMP information -- there are many unrelated tags in the XMP space that are also storing the location data
    # exiftool '-gps*=' -xmp:all= ./images/source -o ./images/output
    subprocess.call(["exiftool", "-gps*=", "-xmp:all=", f"{os.path.abspath(path_images)}", "-o", f"{os.path.abspath(path_output)}"])
    for key in images.keys():
        img = cast(GeoImage, images[key])
        if img.has_georeference:
            subprocess.call(["exiftool", "-overwrite_original", f"-GPSLatitude*={img.lat}", f"-GPSLongitude*={img.lon}", f"-GPSAltitude*={img.height}", f"{os.path.abspath(path_output)}/{img.name}"])

if __name__ == '__main__':
    generate_scalers()
    load_images()
    if process_scaling():
        generate_kml()
        saveNewFiles()
    else:
        print("Due to UTM Zone conflicts, images were not processed.")