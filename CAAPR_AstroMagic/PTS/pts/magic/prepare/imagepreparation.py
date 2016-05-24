#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.preparation.imagepreparation Contains the ImagePreparer class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import io
import imageio
import numpy as np

# Import astronomical modules
from astropy.units import Unit

# Import the relevant PTS classes and modules
from ..core.frame import Frame
from ..basics.coordinatesystem import CoordinateSystem
from ..basics.mask import Mask
from ..sources.extractor import SourceExtractor
from ..sky.skysubtractor import SkySubtractor
from ...core.basics.configurable import Configurable
from ...core.tools.logging import log
from ...modeling.preparation import unitconversion
from ...core.tools import special
from ...core.basics.animatedgif import AnimatedGif
from ...core.tools import filesystem as fs
from ...core.tools import time
from ..tools import plotting

# -----------------------------------------------------------------

class ImagePreparer(Configurable):

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
        super(ImagePreparer, self).__init__(config, "modeling")

        # -- Attributes --

        # The image
        self.image = None

        # The regions
        self.galaxy_region = None
        self.star_region = None
        self.saturation_region = None
        self.other_region = None

        # The segmentation maps
        self.galaxy_segments = None
        self.star_segments = None
        self.other_segments = None

        # The principal ellipse and saturation region in sky coordinates
        self.principal_ellipse_sky = None
        self.saturation_region_sky = None

        # The path to the directory where the visualisation output should be placed
        self.visualisation_path = None

    # -----------------------------------------------------------------

    @classmethod
    def from_arguments(cls, arguments):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Create a new class instance
        preparer = cls()

        # The path to the reference image (for rebinning)
        preparer.config.rebinning.rebin_to = arguments.reference

        # The path to the convolution kernel
        preparer.config.convolution.kernel_path = arguments.kernel

        # The calibration error (in magnitude or percentage)
        preparer.config.uncertainties.calibration_error = arguments.calibration

        # The galactic attenuation
        preparer.config.attenuation = arguments.attenuation

        # Write the results of intermediate steps
        preparer.config.write_steps = arguments.steps

        # Set the output path
        preparer.config.output_path = arguments.output

        # Set flags
        preparer.config.calculate_calibration_uncertainties = True
        preparer.config.extract_sources = True
        preparer.config.correct_for_extinction = True
        preparer.config.convert_unit = True
        preparer.config.convolve = True
        preparer.config.rebin = True
        preparer.config.subtract_sky = True
        preparer.config.set_uncertainties = True

        # Advanced options
        if arguments.sky_annulus_inner is not None: preparer.config.sky_subtraction.mask.annulus_inner_factor = arguments.sky_annulus_inner
        if arguments.sky_annulus_outer is not None: preparer.config.sky_subtraction.mask.annulus_outer_factor = arguments.sky_annulus_outer
        if arguments.convolution_remote is not None: preparer.config.convolution.remote = arguments.convolution_remote

        # Return the new instance
        return preparer

    # -----------------------------------------------------------------

    def run(self, image, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments, visualisation_path=None):

        """
        This function ...
        :param image:
        :param galaxy_region:
        :param star_region:
        :param saturation_region:
        :param other_region:
        :param galaxy_segments:
        :param star_segments:
        :param other_segments:
        :param visualisation_path:
        :return:
        """

        # 1. Call the setup function
        self.setup(image, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments, visualisation_path)

        # 2. Calculate the calibration uncertainties
        if self.config.calculate_calibration_uncertainties: self.calculate_calibration_uncertainties()

        # 3. Extract stars and galaxies from the image
        if self.config.extract_sources: self.extract_sources()

        # 4. If requested, correct for galactic extinction
        if self.config.correct_for_extinction: self.correct_for_extinction()

        # 5. If requested, convert the unit
        if self.config.convert_unit: self.convert_unit()

        # 6. If requested, convolve
        if self.config.convolve: self.convolve()

        # 7. If requested, rebin
        if self.config.rebin: self.rebin()

        # 8. If requested, subtract the sky
        if self.config.subtract_sky: self.subtract_sky()

        # 9. If requested, set the uncertainties
        if self.config.set_uncertainties: self.set_uncertainties()

        # 10. If requested, crop to a smaller coordinate grid
        if self.config.crop: self.crop()

        # 11. Save the result
        self.save_result()

    # -----------------------------------------------------------------

    def setup(self, image, galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments, visualisation_path):

        """
        This function ...
        :param image:
        :param galaxy_region:
        :param star_region:
        :param saturation_region:
        :param other_region:
        :param galaxy_segments:
        :param star_segments:
        :param other_segments:
        :param visualisation_path:
        :return:
        """

        # -- Children --

        # Add extractor and sky subtractor
        self.add_child("extractor", SourceExtractor, self.config.extraction)
        self.add_child("sky_subtractor", SkySubtractor, self.config.sky_subtraction)

        if self.config.write_steps:

            # -- Source extraction --

            self.extractor.config.write_catalogs = True
            self.extractor.config.write_statistics = True
            self.extractor.config.write_regions = True
            self.extractor.config.write_masked_frames = True

            # -- Sky subtraction --

        # Call the setup function of the base class
        super(ImagePreparer, self).setup()

        # Make a local reference to the passed image (with mask)
        self.image = image

        # Make local references to the regions
        self.galaxy_region = galaxy_region
        self.star_region = star_region
        self.saturation_region = saturation_region
        self.other_region = other_region

        # Make local references to the segmentation maps
        self.galaxy_segments = galaxy_segments
        self.star_segments = star_segments
        self.other_segments = other_segments

        # Set the visualisation path
        self.visualisation_path = visualisation_path

    # -----------------------------------------------------------------

    def calculate_calibration_uncertainties(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the calibration uncertainties ...")

        # Add the calibration uncertainty defined in (AB) magnitude
        if "mag" in self.config.uncertainties.calibration_error:

            # -----------------------------------------------------------------

            # Convert the frame into AB magnitudes
            invalid = Mask.is_zero_or_less(self.image.frames.primary)
            ab_frame = unitconversion.jansky_to_ab(self.image.frames.primary)
            # Set infinites to zero
            ab_frame[invalid] = 0.0

            # -----------------------------------------------------------------

            # The calibration uncertainty in AB magnitude
            mag_error = float(self.config.uncertainties.calibration_error.split("mag")[0])

            # a = image[mag] - mag_error
            a = ab_frame - mag_error

            # b = image[mag] + mag_error
            b = ab_frame + mag_error

            # Convert a and b to Jy
            a = unitconversion.ab_mag_zero_point.to("Jy").value * np.power(10.0, -2./5.*a)
            b = unitconversion.ab_mag_zero_point.to("Jy").value * np.power(10.0, -2./5.*b)

            # c = a[Jy] - image[Jy]
            #c = a - jansky_frame
            c = a - self.image.frames.primary

            # d = image[Jy] - b[Jy]
            #d = jansky_frame - b
            d = self.image.frames.primary - b

            # ----------------------------------------------------------------- BELOW: if frame was not already in Jy

            # Calibration errors = max(c, d)
            #calibration_errors = np.maximum(c, d)  # element-wise maxima
            #calibration_errors[invalid] = 0.0 # set zero where AB magnitude could not be calculated

            #relative_calibration_errors = calibration_errors / jansky_frame
            #relative_calibration_errors[invalid] = 0.0

            # Check that there are no infinities or nans in the result
            #assert not np.any(np.isinf(relative_calibration_errors)) and not np.any(np.isnan(relative_calibration_errors))

            # The actual calibration errors in the same unit as the data
            #calibration_frame = self.image.frames.primary * relative_calibration_errors

            # -----------------------------------------------------------------

            calibration_frame = np.maximum(c, d) # element-wise maxima
            calibration_frame[invalid] = 0.0 # set zero where AB magnitude could not be calculated

            new_invalid = Mask.is_nan(calibration_frame) + Mask.is_inf(calibration_frame)
            calibration_frame[new_invalid] = 0.0

            # Check that there are no infinities or nans in the result
            assert not np.any(np.isinf(calibration_frame)) and not np.any(np.isnan(calibration_frame))

            # -----------------------------------------------------------------

        # The calibration uncertainty is expressed in a percentage (from the flux values)
        elif "%" in self.config.uncertainties.calibration_error:

            # Calculate calibration errors with percentage
            fraction = float(self.config.uncertainties.calibration_error.split("%")[0]) * 0.01
            calibration_frame = self.image.frames.primary * fraction

        # Unrecognized calibration error (not a magnitude, not a percentage)
        else: raise ValueError("Unrecognized calibration error")

        # Add the calibration frame
        self.image.add_frame(calibration_frame, "calibration_errors")

        # Inform the user
        log.success("Calibration uncertainties calculated")

    # -----------------------------------------------------------------

    def extract_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Extracting the sources ...")

        # Create an animation to show the result of this step
        if self.visualisation_path is not None:

            # Create an animation to show the result of the source extraction step
            max_frame_value = np.nanmax(self.image.frames.primary)
            animation = AnimatedGif()
            buf = io.BytesIO()
            plotting.plot_box(self.image.frames.primary, path=buf, format="png", vmin=0.0, vmax=max_frame_value)
            buf.seek(0)
            im = imageio.imread(buf)
            buf.close()
            animation.add_frame(im)

            # Create an animation to show the progress of the SourceExtractor
            source_extractor_animation = AnimatedGif()
            source_extractor_animation.fps = 1 # 1 frame per second because the frames are very distinct
        else:
            animation = None
            source_extractor_animation = None

        # Run the extractor
        self.extractor.run(self.image.frames.primary, self.galaxy_region, self.star_region, self.saturation_region,
                           self.other_region, self.galaxy_segments, self.star_segments, self.other_segments, source_extractor_animation)

        # Write the animation
        if self.visualisation_path is not None:

            # Determine the path to the animation
            path = fs.join(self.visualisation_path, time.unique_name(self.image.name + "_sourceextraction") + ".avi")

            # Save the animation
            source_extractor_animation.save(path)

            # ----

            buf = io.BytesIO()
            plotting.plot_box(self.image.frames.primary, path=buf, format="png", vmin=0.0, vmax=max_frame_value)
            buf.seek(0)
            im = imageio.imread(buf)
            buf.close()
            animation.add_frame(im)

            # Determine the path to the animation
            path = fs.join(self.visualisation_path, time.unique_name(self.image.name + "_imagepreparation_extractsources") + ".gif")

            # Save the animation
            animation.save(path)

        # Add the sources mask to the image
        self.image.add_mask(self.extractor.mask, "sources")

        # Get the principal ellipse in sky coordinates
        self.principal_ellipse_sky = self.extractor.principal_ellipse.to_sky(self.image.wcs)

        # Get the saturation region in sky coordinates
        self.saturation_region_sky = self.saturation_region.to_sky(self.image.wcs) if self.saturation_region is not None else None

        # Write intermediate result
        if self.config.write_steps: self.write_intermediate_result("extracted.fits")

        # Inform the user
        log.success("Sources extracted")

    # -----------------------------------------------------------------

    def correct_for_extinction(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Correcting for galactic extinction ...")

        # Correct the primary frame for galactic extinction
        self.image.frames.primary *= 10**(0.4 * self.config.attenuation)

        # Write intermediate result
        if self.config.write_steps: self.write_intermediate_result("corrected_for_extinction.fits")

        # Inform the user
        log.success("Galactic extinction correction finished")

    # -----------------------------------------------------------------

    def convert_unit(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Converting to surface brightness units ...")

        # Run the unit conversion
        #self.unit_converter.run(self.image)

        assert self.image.unit == Unit("Jy/pix")

        # Get pixelscale
        pixelscale = self.image.xy_average_pixelscale

        # Conversion from Jy / pix to MJy / pix
        conversion_factor = 1e-6

        # Conversion from MJy / pix to MJy / sr
        conversion_factor *= (1.0/pixelscale**2).to("pix2/sr").value

        # Multiply the image with the conversion factor
        self.image *= conversion_factor

        # Set the new unit
        self.image.unit = Unit("MJy/sr")

        # Write intermediate result
        if self.config.write_steps: self.write_intermediate_result("converted_unit.fits")

        # Inform the user
        log.success("Units converted")

    # -----------------------------------------------------------------

    def convolve(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Convolving the image with kernel " + self.config.convolution.kernel_path + " ...")

        # Create an animation to show the result of this step
        if self.visualisation_path is not None:

            max_frame_value = np.nanmax(self.image.frames.primary)
            animation = AnimatedGif()
            buf = io.BytesIO()
            plotting.plot_box(self.image.frames.primary, path=buf, format="png", vmin=0.0, vmax=max_frame_value)
            buf.seek(0)
            im = imageio.imread(buf)
            buf.close()
            animation.add_frame(im)

        else: animation = None

        # Check whether the convolution has to be performed remotely
        if self.config.convolution.remote is not None:

            # Inform the user
            log.info("Convolution will be performed remotely on host '" + self.config.convolution.remote + "' ...")

            # Check whether the FWHM of the kernel is defined
            kernel = Frame.from_file(self.config.convolution.kernel_path)
            if kernel.fwhm is not None:
                kernel_fwhm = kernel.fwhm
            elif self.config.convolution.kernel_fwhm is not None:
                kernel_fwhm = self.config.convolution.kernel_fwhm
            else: raise RuntimeError("Kernel must either have its FWHM defined in the header or the kernel FWHM must be specified as a configuration option for the ImagePreparer")

            # Perform the remote convolution
            special.remote_convolution(self.image, self.config.convolution.kernel_path, kernel_fwhm, self.config.convolution.remote)

        # The convolution is performed locally
        else:

            # Open the kernel frame
            kernel = Frame.from_file(self.config.convolution.kernel_path)

            # Set the kernel FWHM
            if kernel.fwhm is None and self.config.convolution.kernel_fwhm is not None: kernel.fwhm = self.config.convolution.kernel_fwhm

            # Convolve the image (the primary and errors frame)
            self.image.convolve(kernel, allow_huge=True)

        # Save convolved frame
        if self.config.write_steps: self.write_intermediate_result("convolved.fits")

        # Write the animation
        if self.visualisation_path is not None:

            buf = io.BytesIO()
            plotting.plot_box(self.image.frames.primary, path=buf, format="png", vmin=0.0, vmax=max_frame_value)
            buf.seek(0)
            im = imageio.imread(buf)
            buf.close()
            animation.add_frame(im)

            # Determine the path to the animation
            path = fs.join(self.visualisation_path, time.unique_name(self.image.name + "_imagepreparation_convolve") + ".gif")

            # Save the animation
            animation.save(path)

        # Inform the user
        log.success("Convolution finished")

    # -----------------------------------------------------------------

    def rebin(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Rebinning the image to the pixel grid of " + self.config.rebinning.rebin_to + " ...")

        # Get the coordinate system of the reference frame
        reference_system = CoordinateSystem.from_file(self.config.rebinning.rebin_to)

        # Add a mask to the image that covers the complete current pixel grid
        self.image.add_mask(Mask.full_like(self.image.frames.primary), "padded")

        # Rebin the image (the primary and errors frame)
        self.image.rebin(reference_system)

        # Invert the 'padded' mask -> this mask now covers pixels added to the frame after rebinning
        self.image.masks.padded = self.image.masks.padded.inverse().disk_dilation(radius=10)

        # Save rebinned frame
        if self.config.write_steps: self.write_intermediate_result("rebinned.fits")

        # Inform the user
        log.success("Rebinning finished")

    # -----------------------------------------------------------------

    def subtract_sky(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Subtracting the sky ...")

        # Create an animation to show the result of this step
        if self.visualisation_path is not None:

            # Create an animation to show the result of the sky subtraction step
            max_frame_value = np.nanmax(self.image.frames.primary)
            animation = AnimatedGif()
            buf = io.BytesIO()
            plotting.plot_box(self.image.frames.primary, path=buf, format="png", vmin=0.0, vmax=max_frame_value)
            buf.seek(0)
            im = imageio.imread(buf)
            buf.close()
            animation.add_frame(im)

            # Create an animation to show the progress of the SkySubtractor
            skysubtractor_animation = AnimatedGif()
        else:
            animation = None
            skysubtractor_animation = None

        # Convert the principal ellipse in sky coordinates into pixel coordinates
        principal_ellipse = self.principal_ellipse_sky.to_pixel(self.image.wcs)

        # Convert the saturation region in sky coordinates into pixel coordinates
        if self.saturation_region_sky is not None:
            saturation_region = self.saturation_region_sky.to_pixel(self.image.wcs)
        else: saturation_region = None

        # Create the 'extra' mask (bad and padded pixels)
        extra_mask = None
        if "bad" in self.image.masks:
            # Combine with padded mask or just use bad mask
            if "padded" in self.image.masks: extra_mask = self.image.masks.bad + self.image.masks.padded
            else: extra_mask = self.image.masks.bad
        elif "padded" in self.image.masks: extra_mask = self.image.masks.padded # just use padded mask

        # Run the sky subtractor
        self.sky_subtractor.run(self.image.frames.primary, principal_ellipse, self.image.masks.sources, extra_mask, saturation_region, skysubtractor_animation)

        # Add the sky frame to the image
        self.image.add_frame(self.sky_subtractor.sky_frame, "sky")

        # Add the mask that is used for the sky estimation
        self.image.add_mask(self.sky_subtractor.mask, "sky")

        # Write intermediate result if requested
        if self.config.write_steps: self.write_intermediate_result("sky_subtracted.fits")

        # Write sky annuli maps if requested
        if self.config.write_sky_annuli:

            # Write the apertures frame
            apertures_frame_path = fs.join(self.config.sky_annuli_path, "apertures.fits")
            self.sky_subtractor.apertures_frame.save(apertures_frame_path)

            # Write the apertures mean frame
            apertures_mean_path = fs.join(self.config.sky_annuli_path, "apertures_mean.fits")
            self.sky_subtractor.apertures_mean_frame.save(apertures_mean_path)

            # Write the apertures noise frame
            apertures_noise_path = fs.join(self.config.sky_annuli_path, "apertures_noise.fits")
            self.sky_subtractor.apertures_noise_frame.save(apertures_noise_path)

        # Write the animation
        if self.visualisation_path is not None:

            # Determine the path to the animation
            path = fs.join(self.visualisation_path, time.unique_name(self.image.name + "_skysubtraction") + ".gif")

            # Save the animation
            skysubtractor_animation.save(path)

            buf = io.BytesIO()
            plotting.plot_box(self.image.frames.primary, path=buf, format="png", vmin=0.0, vmax=max_frame_value)
            buf.seek(0)
            im = imageio.imread(buf)
            buf.close()
            animation.add_frame(im)

            # Determine the path to the animation
            path = fs.join(self.visualisation_path, time.unique_name(self.image.name + "_imagepreparation_subtractsky") + ".gif")

            # Save the animation
            animation.save(path)

        # Inform the user
        log.success("Sky subtracted")

    # -----------------------------------------------------------------

    def set_uncertainties(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the uncertainties ...")

        # Add all the errors quadratically: existing error map + large scale variations + pixel to pixel noise + calibration error
        #if "errors" in self.image.frames: self.image.frames.errors = np.sqrt(self.image.frames.errors**2 + self.sky_subtractor.noise**2 + self.image.frames.calibration_errors**2)

        # Calculate the total error map
        errors = np.sqrt(self.sky_subtractor.noise**2 + self.image.frames.calibration_errors**2)
        self.image.add_frame(errors, "errors")

        # Inform the user
        log.success("Uncertainties calculated")

    # -----------------------------------------------------------------

    def crop(self):

        """
        This function ...
        :return:
        """

        # Get the cropping limits
        #x_min = self.config.cropping.limits[0]
        #x_max = self.config.cropping.limits[1]
        #y_min = self.config.cropping.limits[2]
        #y_max = self.config.cropping.limits[3]

        # Crop the image (the primary and errors frame)
        #self.image.crop(x_min, x_max, y_min, y_max)

        pass

    # -----------------------------------------------------------------

    def save_result(self):

        """
        This function ...
        :return:
        """

        # Determine the full path to the result file
        path = self.full_output_path("result.fits")

        # Inform the user
        log.info("Writing resulting image to " + path + " ...")

        # Write out the resulting image
        self.image.save(path, origin=self.name)

    # -----------------------------------------------------------------

    def write_intermediate_result(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Determine the full path to the result file
        path = self.full_output_path(path)

        # Inform the user
        log.info("Writing intermediate result to " + path + " ...")

        # Write out the image
        self.image.save(path, origin=self.name)

# -----------------------------------------------------------------
