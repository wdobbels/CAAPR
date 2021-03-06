#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.magic.extract Extract stars and other objects from an astronomical image.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import argparse

# Import the relevant PTS classes and modules
from pts.magic.core.frame import Frame
from pts.magic.core.image import Image
from pts.magic.basics.region import Region
from pts.magic.misc.imageimporter import ImageImporter
from pts.magic.sources.extractor import SourceExtractor
from pts.core.tools import configuration, logging, time
from pts.core.tools import filesystem as fs
from pts.core.basics.animation import Animation

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()

# Basic
parser.add_argument("image", type=str, help="the name of the input image")

# Configuration
parser.add_argument('--config', type=str, help='the name of a configuration file', default=None)
parser.add_argument("--settings", type=configuration.from_string, help="settings")

# Logging options
parser.add_argument("--debug", action="store_true", help="enable debug logging mode")
parser.add_argument('--report', action='store_true', help='write a report file')

# Input and output
parser.add_argument("-i", "--input", type=str, help="the name of the input directory")
parser.add_argument("-o", "--output", type=str, help="the name of the output directory")

# Input regions
parser.add_argument("--special", type=str, help="the name of the file specifying regions with objects needing special attention")
parser.add_argument("--bad", type=str, help="the name of the file specifying regions that have to be added to the mask of bad pixels")

# The interpolation method to use
parser.add_argument("--interpolation", type=str, help="the interpolation method to use")
parser.add_argument("--disable_sigma_clipping", action="store_true", help="add this option to disable sigma-clipping during the interpolation")

# Visualization
parser.add_argument("--visualise", action="store_true", help="make visualisations")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# If an input directory is given
if arguments.input is not None:

    # Determine the full path to the input directory
    input_path = fs.absolute(arguments.input)

    # Give an error if the input directory does not exist
    if not fs.is_directory(input_path): raise argparse.ArgumentError(input_path, "The input directory does not exist")

# If no input directory is given, assume the input is placed in the current working directory
else: input_path = fs.cwd()

# -----------------------------------------------------------------

# If an output directory is given
if arguments.output is not None:
    
    # Determine the full path to the output directory
    output_path = fs.absolute(arguments.output)
    
    # Create the directory if it does not yet exist
    if not fs.is_directory(output_path): fs.create_directory(output_path)

# If no output directory is given, place the output in the current working directory
else: output_path = fs.cwd()

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = fs.join(output_path, time.unique_name("log") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
log.start("Starting extract ...")

# -----------------------------------------------------------------

# Determine the full path to the image
image_path = fs.absolute(arguments.image)

# Determine the full path to the bad region file
bad_region_path = fs.join(input_path, arguments.bad) if arguments.bad is not None else None

# Import the image
importer = ImageImporter()
importer.run(image_path, bad_region_path=bad_region_path)

# Get the image
image = importer.image

# -----------------------------------------------------------------

# Load the galaxy region
galaxy_region_path = fs.join(input_path, "galaxies.reg")
galaxy_region = Region.from_file(galaxy_region_path) if fs.is_file(galaxy_region_path) else None

# Load the star region
star_region_path = fs.join(input_path, "stars.reg")
star_region = Region.from_file(star_region_path) if fs.is_file(star_region_path) else None

# Load the saturation region
saturation_region_path = fs.join(input_path, "saturation.reg")
saturation_region = Region.from_file(saturation_region_path) if fs.is_file(saturation_region_path) else None

# Load the region of other sources
other_region_path = fs.join(input_path, "other_sources.reg")
other_region = Region.from_file(other_region_path) if fs.is_file(other_region_path) else None

# Load the image with segmentation maps
segments_path = fs.join(input_path, "segments.fits")
segments = Image.from_file(segments_path, no_filter=True)

# Get the segmentation maps
galaxy_segments = segments.frames.galaxies if "galaxies" in segments.frames else None
star_segments = segments.frames.stars if "stars" in segments.frames else None
other_segments = segments.frames.other_sources if "other_sources" in segments.frames else None

# -----------------------------------------------------------------

# If visualisation is enabled, set the visualisation path (=output path)
if arguments.visualise:
    animation = Animation()
    animation.fps = 1
else: animation = None

# -----------------------------------------------------------------

# If a special region is defined
if arguments.special is not None:

    # Determine the full path to the special region file
    path = fs.join(input_path, arguments.special)

    # Inform the user
    log.info("Loading region indicating areas that require special attention from " + path + " ...")

    # Load the region and create a mask from it
    special_region = Region.from_file(path)

# No special region
else: special_region = None

# -----------------------------------------------------------------

# Create an Extractor instance and configure it according to the command-line arguments
extractor = SourceExtractor.from_arguments(arguments)

# Set the interpolation method (if specified)
if arguments.interpolation is not None: extractor.config.interpolation_method = arguments.interpolation

# Set sigma-clipping
if arguments.disable_sigma_clipping: extractor.config.sigma_clip = False

# Run the extractor
extractor.run(image.frames.primary, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments, animation, special_region)

# -----------------------------------------------------------------

# Save the animation
if animation is not None:
    path = fs.join(output_path, "animation.gif")
    animation.save(path)

# -----------------------------------------------------------------

# Inform the user
log.info("Writing the result ...")

# Determine the path to the result
result_path = fs.join(output_path, image.name + ".fits")

# Save the resulting image as a FITS file
image.frames.primary.save(result_path, header=image.original_header)

# -----------------------------------------------------------------

# Inform the user
log.info("Writing the mask ...")

# Determine the path to the mask
mask_path = fs.join(output_path, "mask.fits")

# Save the total mask as a FITS file
Frame(extractor.mask.astype(float)).save(mask_path)

# -----------------------------------------------------------------
