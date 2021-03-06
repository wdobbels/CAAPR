#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.photometry.photometry Contains the PhotoMeter class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np

# Import the relevant PTS classes and modules
from ...magic.core.image import Image
from .component import PhotometryComponent
from .sedfetching import SEDFetcher
from ...core.tools import filesystem as fs
from ...core.tools.logging import log
from ..core.sed import ObservedSED
from ...core.basics.errorbar import ErrorBar
from ...core.tools import tables
from ...core.plot.sed import SEDPlotter

# -----------------------------------------------------------------

# CHRIS:

# For SPIRE: Section 5.2.12 of the SPIRE Handbook (http://herschel.esac.esa.int/Docs/SPIRE/spire_handbook.pdf)
# provides the "official" way of performing aperture corrections; we specifically care about the "Extended source photometry
# (starting from extended source maps)" part. If you're using arbitrarily-large, non-circular apertures, you basically
# have to use maps of the beam profile to work out what fraction of the flux is outside your aperture.
# Those can be retrieved from the SPIRE calibration wiki (http://herschel.esac.esa.int/twiki/bin/view/Public/SpirePhotometerBeamProfile2).

# In the meantime, I'm working on sensible automated aperture-corrections - current plan is to assume that the underlying
# flux distribution follows a 2D-sersic profile, and so fit to each source a 2D-sersic convolved with the beam, and hence estimate the amount of flux that gets spread beyond the aperture. Hopefully it will be easily applicable to your work too.

# For PACS: The most up-to-date document on the PACS calibration wiki (http://herschel.esac.esa.int/twiki/pub/Public/PacsCalibrationWeb/bolopsf_22.pdf)
# and its accompanying tar.gz (ftp://ftp.sciops.esa.int/pub/hsc-calibration/PACS/PSF/PACSPSF_PICC-ME-TN-033_v2.2.tar.gz)
# give the most recent PACS beam profiles, and encircled energy fractions (EEFs) for different aperture sizes in the
# various scanning modes.

# PIETER:

# Zie bijlage voor de tabellen met de correcties voor de enclosed energy fraction (EEF) voor elke aperture size for PACS en SPIRE.
# Voor de aperture size moet ge mogelijks voor elke band een andere waarde gebruiken (door evt de beamsize in rekening te brengen ofzo).
# De flux in elke band moet dan gedeeld worden door de correction factor voor die band, gebruik makend van de aperture size in die band.

# De Growth_Curve_Final_XXmicron.dat geven de aperture size in arcsec en de correction factor voor de 2 PACS bands.

# De PSF_correction_HATLAS_SPIRE.dat geeft de aperture size in arcsec en dan de correction factors for 250um,350um en 500um.

# Deze corrections zijn voor een centrale pointsource en zijn dus een soort minimum correctie voor een extended source.
# Deze minimum correcties worden doorgaands toegepast op extended sources omdat ze een goed genoege 1ste orde benadering zijn.

# -----------------------------------------------------------------

class PhotoMeter(PhotometryComponent):
    
    """
    This class...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(PhotoMeter, self).__init__(config)

        # The list of images
        self.images = []

        # The disk ellipse
        self.disk_ellipse = None

        # The SED
        self.sed = None

        # The SEDFetcher
        self.sed_fetcher = None

        # The differences
        self.differences = None

    # -----------------------------------------------------------------

    @classmethod
    def from_arguments(cls, arguments):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Create a new PhotoMeter instance
        photometer = cls(arguments.config)

        # Set the modeling path
        photometer.config.path = arguments.path

        # Return the new instance
        return photometer

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Load the truncated images
        self.load_images()

        # 3. Calculate the Enclosed Energy Fractions
        self.calculate_eefs()

        # 3. Do the photometry
        self.do_photometry()

        # 4. Get the photometric flux points from the literature for comparison
        self.get_references()

        # 5. Calculate the differences between the calculated photometry and the reference SEDs
        self.calculate_differences()

        # 6. Writing
        self.write()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(PhotoMeter, self).setup()

        # Create an observed SED
        self.sed = ObservedSED()

        # Create an SEDFetcher instance
        self.sed_fetcher = SEDFetcher()

    # -----------------------------------------------------------------

    def load_images(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the images ...")

        # Loop over all files found in the truncation directory
        for path, name in fs.files_in_path(self.truncation_path, extension="fits", returns=["path", "name"]):

            # Skip the H alpha image
            if "Halpha" in name: continue

            # Debugging
            log.debug("Loading the " + name + " image ...")

            # Open the truncated image
            image = Image.from_file(path)

            # Check that the image has a primary and and errors frame
            if "primary" not in image.frames:
                log.warning("The " + name + " image does not contain a primary frame: skipping")
                continue
            if "errors" not in image.frames:
                log.warning("The " + name + " image does not contain an errors frame: skipping")
                continue

            # Add the image to the list
            self.images.append(image)

    # -----------------------------------------------------------------

    def calculate_eefs(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def do_photometry(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Performing the photometry calculation ...")

        # Loop over all the images
        for image in self.images:

            # Debugging
            log.debug("Performing photometry for " + image.name + " image ...")

            # Debugging
            log.debug("Converting image to Jansky ...")

            # Convert from MJy/sr to Jy/sr
            conversion_factor = 1.0
            conversion_factor *= 1e6

            # Conversion from Jy / sr to Jy / pixel
            pixelscale = image.average_pixelscale
            pixel_factor = (1.0/pixelscale**2).to("pix2/sr").value
            conversion_factor /= pixel_factor

            # Frame in Janskys
            jansky_frame = image.frames.primary * conversion_factor

            # Error farme in Janskys
            jansky_errors_frame = image.frames.errors * conversion_factor

            # Debugging
            log.debug("Calculating the total flux and flux error ...")

            # Calculate the total flux in Jansky
            flux = np.sum(jansky_frame)

            # Calculate the total flux error in Jansky
            flux_error = np.sum(jansky_errors_frame)

            # Create errorbar
            errorbar = ErrorBar(float(flux_error))

            # Add this entry to the SED
            self.sed.add_entry(image.filter, flux, errorbar)

    # -----------------------------------------------------------------

    def get_references(self):

        """
        This function ...
        :return:
        """

        # Specify which references should be consulted
        self.sed_fetcher.config.catalogs = ["GALEX", "2MASS", "SINGS", "LVL", "Spitzer", "Spitzer/IRS", "IRAS", "IRAS-FSC", "S4G", "Brown", "Planck"]

        # Fetch the reference SEDs
        self.sed_fetcher.run(self.galaxy_name)

    # -----------------------------------------------------------------

    def calculate_differences(self):

        """
        This function ...
        :return:
        """

        # Get list of instruments, bands and fluxes of the calculated SED
        instruments = self.sed.instruments()
        bands = self.sed.bands()
        fluxes = self.sed.fluxes(unit="Jy", add_unit=False)

        # The number of data points
        number_of_points = len(instruments)

        # Initialize data and names
        reference_labels = self.sed_fetcher.seds.keys()
        data = [[] for _ in range(len(reference_labels)+3)]
        names = ["Instrument", "Band", "Flux"]
        for label in reference_labels:
            names.append(label)

        # Loop over the different points in the calculated SED
        for i in range(number_of_points):

            # Add instrument, band and flux
            data[0].append(instruments[i])
            data[1].append(bands[i])
            data[2].append(fluxes[i])

            column_index = 3

            # Loop over the different reference SEDs
            for label in reference_labels:

                relative_difference = None

                # Loop over the data points in the reference SED
                for j in range(len(self.sed_fetcher.seds[label].table["Wavelength"])):

                    if self.sed_fetcher.seds[label].table["Instrument"][j] == instruments[i] and self.sed_fetcher.seds[label].table["Band"][j] == bands[i]:

                        difference = fluxes[i] - self.sed_fetcher.seds[label].table["Flux"][j]
                        relative_difference = difference / fluxes[i] * 100.

                        # Break because a match has been found within this reference SED
                        break

                # Add percentage to the table (or None if no match was found in this reference SED)
                data[column_index].append(relative_difference)

                column_index += 1

        # Create table of differences
        self.differences = tables.new(data, names=names)

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write SED table
        self.write_sed()

        # Write the differences
        self.write_differences()

        # Plot the SED
        self.plot_sed()

        # Plot the SED with references
        self.plot_sed_with_references()

    # -----------------------------------------------------------------

    def write_sed(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing SED to a data file ...")

        # Save the SED
        self.sed.save(self.observed_sed_path)

    # -----------------------------------------------------------------

    def write_differences(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the percentual differences with reference fluxes to a data file ...")

        # Determine the full path to the output file
        path = fs.join(self.phot_path, "differences.dat")

        # Save the differences table
        tables.write(self.differences, path, format="ascii.ecsv")

    # -----------------------------------------------------------------

    def plot_sed(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting the SED ...")

        # Create a new SEDPlotter instance
        plotter = SEDPlotter(self.galaxy_name)

        # Add the SED
        plotter.add_observed_sed(self.sed, "PTS")

        # Determine the full path to the plot file
        path = fs.join(self.phot_path, "sed.pdf")
        plotter.run(path)

    # -----------------------------------------------------------------

    def plot_sed_with_references(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting the SED with reference fluxes ...")

        # Create a new SEDPlotter instance
        plotter = SEDPlotter(self.galaxy_name)

        # Add the SED
        plotter.add_observed_sed(self.sed, "PTS")

        # Add the reference SEDs
        for label in self.sed_fetcher.seds: plotter.add_observed_sed(self.sed_fetcher.seds[label], label)

        # Determine the full path to the plot file
        path = fs.join(self.phot_path, "sed_with_references.pdf")
        plotter.run(path)

# -----------------------------------------------------------------
