#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.core.image Contains the Image class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
import matplotlib.pyplot as plt

# Import astronomical modules
import aplpy
from astropy.io import fits
from astropy import units as u

# Import the relevant PTS classes and modules
from ..basics.layers import Layers
from ..basics.region import Region
from ..basics.mask import Mask
from ..basics.coordinatesystem import CoordinateSystem
from .frame import Frame
from ..tools import headers, transformations
from ...core.tools import filesystem
from ...core.tools.logging import log

# -----------------------------------------------------------------

class Image(object):

    """
    This class ...
    """

    def __init__(self, name="untitled"):

        """
        The constructor ...
        :param name:
        :return:
        """

        # Initialize a set of layers to represent image frames, masks and regions
        self.frames = Layers()
        self.masks = Layers()
        self.regions = Layers()

        # The image name and path
        self.name = name
        self.path = None

        # The original image header
        self.original_header = None

        # The dictionary containing meta information
        self.metadata = dict()

        # Temporary fix because fwhm is sometimes not transferred to a new primary Frame and therefore fwhm information is lost on the complete image
        self._fwhm = None

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path, name=None, always_call_first_primary=True, hdulist_index=0):

        """
        This function ...
        :param path:
        :param name:
        :param always_call_first_primary:
        :param hdulist_index:
        :return:
        """

        # If no name is given, determine the name from the file path
        if name is None: name = filesystem.strip_extension(filesystem.name(path))

        # Create a new image
        image = cls(name)

        # Set the image path
        image.path = path

        # Load the image frames
        image.load_frames(path, always_call_first_primary=always_call_first_primary, hdulist_index=hdulist_index)

        # Return the image
        return image

    # -----------------------------------------------------------------

    @property
    def shape(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None
        return self.frames.primary.shape

    # -----------------------------------------------------------------

    @property
    def xsize(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None
        return self.frames.primary.xsize

    # -----------------------------------------------------------------

    @property
    def ysize(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None
        return self.frames.primary.ysize

    # -----------------------------------------------------------------

    @property
    def filter(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None

        # Return the filter of the primary frame
        return self.frames.primary.filter

    # -----------------------------------------------------------------

    @property
    def wavelength(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None

        # Return the wavelength of the primary frame
        return self.frames.primary.wavelength

    # -----------------------------------------------------------------

    @property
    def unit(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None

        # Return the unit of the primary frame
        return self.frames.primary.unit

    # -----------------------------------------------------------------

    @property
    def pixelscale(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None

        # Return the pixelscale of the primary frame
        return self.frames.primary.pixelscale

    # -----------------------------------------------------------------

    @property
    def xy_average_pixelscale(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None

        # Return the averaged pixelscale of the primary frame
        return self.frames.primary.xy_average_pixelscale

    # -----------------------------------------------------------------

    @property
    def fwhm(self):

        """
        This function ...
        :return:
        """

        if self._fwhm is not None: return self._fwhm

        if "primary" not in self.frames: return None

        # Return the FWHM of the primary frame
        return self.frames.primary.fwhm

    # -----------------------------------------------------------------

    @property
    def wcs(self):

        """
        This function ...
        :return:
        """

        if "primary" not in self.frames: return None

        # Return the wcs of the primary frame
        return self.frames.primary.wcs

    # -----------------------------------------------------------------

    def __repr__(self):

        """
        This function ...
        :return:
        """

        return "<" + self.__class__.__name__ + " '" + self.name + "' with " + str(len(self.frames)) + " frame, " + str(len(self.regions)) + " regions and " + str(len(self.masks)) + " masks>"

    # -----------------------------------------------------------------

    def save(self, path=None, add_metadata=False, origin=None, add_masks=True):

        """
        This function exports the image (frames and masks) as a datacube into FITS file.
        :param path:
        :param add_metadata:
        :param origin:
        :param add_masks:
        :return:
        """

        if path is None: path = self.path

        # Create an array to contain the data cube
        datacube = []

        plane_index = 0

        header = None

        # Export all frames to the specified file
        for frame_name in self.frames:

            # Inform the user that this frame will be saved to the image file
            log.info("Exporting the " + frame_name + " frame to " + path)

            if header is None: header = self.frames[frame_name].header

            # Check if the coordinate system of this frame matches that of the other frames
            #if header != self.frames[frame_name].header: raise ValueError("The WCS of the different frames does not match")

            # Add this frame to the data cube, if its coordinates match those of the primary frame
            datacube.append(self.frames[frame_name])
            
            # Add the name of the frame to the header
            header["PLANE" + str(plane_index)] = frame_name + " [frame]"

            # Increment the plane index
            plane_index += 1

        # Add the masks
        if add_masks:

            # Export all masks to the specified file
            for mask_name in self.masks:

                # Inform the user that this mask will be saved to the image file
                log.info("Exporting the " + mask_name + " mask to " + path)

                # Add this mask to the data cube
                datacube.append(self.masks[mask_name].astype(int))

                # Add the name of the mask to the header
                header["PLANE" + str(plane_index)] = mask_name + " [mask]"

                # Increment the plane index
                plane_index += 1

        # Add the meta information to the header
        if add_metadata:
            for key in self.metadata:
                try: header[key] = self.metadata[key]
                except ValueError: pass # Some values in the header gives errors in Astropy when adding them again to this new header ... (e.g. ValueError: Illegal value: = 'created by T.H. Jarrett'.)

        # Set plane information
        if plane_index > 1:
            header["NAXIS"] = 3
            header["NAXIS3"] = plane_index

        # Set unit, FWHM and filter description
        if self.unit is not None: header.set("SIGUNIT", str(self.unit), "Unit of the map")
        if self.fwhm is not None: header.set("FWHM", self.fwhm.to("arcsec").value, "[arcsec] FWHM of the PSF")
        if self.filter is not None: header.set("FILTER", self.filter.description(), "Filter used for this observation")

        # Add origin description
        if origin is not None: header["ORIGIN"] = origin
        else: header["ORIGIN"] = "Image class of PTS package"

        # Create the HDU from the data array and the header
        hdu = fits.PrimaryHDU(np.array(datacube), header)

        # Write the HDU to a FITS file
        hdu.writeto(path, clobber=True)

        # Update the path
        self.path = path

        # Inform the user that the file has been created
        log.info("File " + path + " created")

    # -----------------------------------------------------------------

    def import_region(self, path, name, overwrite=False):

        """
        This function imports a new region from a DS9 region file
        :param path:
        :param name:
        :param overwrite:
        :return:
        """

        # Check if the region file exists
        if not filesystem.is_file(path): raise IOError("The region file does not exist")

        # Create an Region object from the regions file
        region = Region.from_file(path)

        # Add the region to the set of regions
        self.add_region(region, name, overwrite)

    # -----------------------------------------------------------------

    def get_state(self):

        """
        This function ...
        :return:
        """

        # Create an empty dictionary to contain the state of the current image
        state = dict()

        # Loop over all frames, regions and masks and record whether they are selected
        for frame_name in self.frames: state["frames/"+frame_name] = self.frames[frame_name].selected
        for region_name in self.regions: state["regions/"+region_name] = self.regions[region_name].selected
        for mask_name in self.masks: state["masks/"+mask_name] = self.masks[mask_name].selected

        # Return the state dictionary
        return state

    # -----------------------------------------------------------------

    def set_state(self, state):

        """
        This function ...
        :param state:
        :return:
        """

        # Loop over the entries in the state dictionary
        for identifier, selected in state.items():

            # Split the layer identifier into the layer type and the actual name of that layer
            layer_type, name = identifier.split("/")

            # Set the appropriate flag
            if layer_type == "frames": self.frames[name].selected = selected
            elif layer_type == "regions": self.regions[name].selected = selected
            elif layer_type == "masks": self.masks[name].selected = selected
            else: raise ValueError("Invalid state dictionary")

    # -----------------------------------------------------------------

    @unit.setter
    def unit(self, unit):

        """
        This function ...
        :param unit:
        :return:
        """

        # Loop over all frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Setting the unit of the " + frame_name + " frame to " + str(unit) + " ...")

            # Set the unit for this frame
            self.frames[frame_name].unit = unit

    # -----------------------------------------------------------------

    @fwhm.setter
    def fwhm(self, fwhm):

        """
        This function ...
        :param fwhm:
        :return:
        """

        self._fwhm = fwhm

        # Loop over all frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Setting the FWHM of the " + frame_name + " frame to " + str(fwhm) + " ...")

            # Set the unit for this frame
            self.frames[frame_name].fwhm = fwhm

    # -----------------------------------------------------------------

    @filter.setter
    def filter(self, filter):

        """
        This function ...
        :param filter:
        :return:
        """

        # Loop over all frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Setting the filter of the " + frame_name + " frame to " + filter.description() + " ...")

            # Set the filter for this frame
            self.frames[frame_name].filter = filter

    # -----------------------------------------------------------------

    @wcs.setter
    def wcs(self, wcs):

        """
        This function ...
        :param wcs:
        :return:
        """

        # Loop over all frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Setting the coordinate system of the " + frame_name + " frame ...")

            # Set the wcs for this frame
            self.frames[frame_name].wcs = wcs

    # -----------------------------------------------------------------

    def convert_to(self, unit):

        """
        This function ...
        :param unit:
        """

        # Inform the user
        log.info("Converting the unit of the image from " + str(self.unit) + " to " + str(unit) + " ...")

        # Calculate the conversion factor
        a = 1.0 * self.unit
        b = 1.0 * unit
        factor = (a/b).decompose().value

        # Debug message
        log.debug("Conversion factor = " + str(factor))

        # Multiply the image with the conversion factor
        self.__imul__(factor)

        # Set the new unit
        self.unit = unit

    # -----------------------------------------------------------------

    def convolve(self, kernel):

        """
        This function ...
        :param kernel:
        """

        # Loop over all currently selected frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Convolving the " + frame_name + " frame ...")

            # Convolve this frame
            self.frames[frame_name] = self.frames[frame_name].convolved(kernel)

    # -----------------------------------------------------------------

    def rebin(self, reference_wcs):

        """
        This function ...
        :param reference_wcs:
        """

        # Create a copy of the current wcs
        original_wcs = self.wcs.deepcopy()

        # Loop over all currently selected frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Rebinning the " + frame_name + " frame ...")

            # Rebin this frame (the reference wcs is automatically set in the new frame)
            self.frames[frame_name] = self.frames[frame_name].rebinned(reference_wcs)

        # Loop over the masks
        for mask_name in self.masks:

            # Inform the user
            log.info("Rebinning the " + mask_name + " mask ...")

            # Rebin this mask
            data = transformations.new_align_and_rebin(self.masks[mask_name].astype(float), original_wcs, reference_wcs)

            # Return the rebinned mask
            # data, name, description
            self.masks[mask_name] = Mask(data > 0.5, name=self.masks[mask_name].name, description=self.masks[mask_name].description)

    # -----------------------------------------------------------------

    def crop(self, x_min, x_max, y_min, y_max):

        """
        This function ...
        :param x_min:
        :param x_max:
        :param y_min:
        :param y_max:
        """

        # Loop over all currently selected frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Cropping the " + frame_name + " frame")

            # Rebin this frame
            self.frames[frame_name] = self.frames[frame_name].crop(x_min, x_max, y_min, y_max)

        # Loop over all masks
        for mask_name in self.masks:

            # Inform the user
            log.info("Cropping the " + mask_name + " mask")

            # Rebin this mask
            self.masks[mask_name] = self.masks[mask_name][y_min:y_max, x_min:x_max]

    # -----------------------------------------------------------------

    def plot(self, path=None, color=True, grid=False, blacknan=False, publication=False):

        """
        This function shows a plot of the currently selected frame, combined with the active regions and masks
        :param path:
        :param color:
        :param grid:
        :param blacknan:
        :param publication:
        :return:
        """

        # Get the currently active frame
        frame = self.frames.get_selected()[0]

        # Create a total mask of the currently active masks
        total_mask = self.combine_masks(return_mask=True)

        # Mask the frame with nans
        maskedimage = np.ma.array(self.frames[frame], mask = total_mask)
        image_with_nans =  maskedimage.filled(np.NaN)

        # Create a HDU from this frame with the image header
        hdu = fits.PrimaryHDU(image_with_nans, self.original_header)

        if path is None:

            # Create a figure canvas
            figure = plt.figure(figsize=(12, 12))

            # Create a figure from this frame
            plot = aplpy.FITSFigure(hdu, figure=figure)

        else:

            # Create a figure from this frame
            plot = aplpy.FITSFigure(hdu)

        if color:

            # Plot in color scale
            plot.show_colorscale()

        else:

            # Plot in gray scale
            plot.show_grayscale()

        # Add a color bar
        plot.add_colorbar()

        if blacknan:

            # Set the nan color to black
            plot.set_nan_color('black')

        if grid:

            # Add a grid
            plot.add_grid()

        # If requested, use the 'publication' theme
        if publication: plot.set_theme('publication')

        # Add the regions
        for region in self.regions.get_selected():

            # Get the shape list
            shapes = self.regions[region].region.as_imagecoord(self.original_header)

            # Add these shapes to the plot
            plot.show_regions(shapes)

        if path is None:

            #plt.draw()
            #plt.close('all') # redundant
            #plt.show(block=False)
            plt.show()

        else: plot.save(path)

    # -----------------------------------------------------------------

    def delete_frame(self, frame_name):

        """
        This function removes the specified frame
        :param frame_name:
        :return:
        """

        # Inform the user
        log.info("Deleting the " + frame_name + " frame ...")

        # Remove this frame from the frames dictionary
        del self.frames[frame_name]

    # -----------------------------------------------------------------

    def delete_region(self, region_name):

        """
        This function removes the specified region
        :param region_name:
        :return:
        """

        # Inform the user
        log.info("Deleting the " + region_name + " region ...")

        # Remove this region from the regions dictionary
        del self.regions[region_name]

    # -----------------------------------------------------------------

    def delete_mask(self, mask_name):

        """
        This function removes the specified mask
        :param mask_name:
        :return:
        """

        # Inform the user
        log.info("Deleting the " + mask_name + " mask ...")

        # Remove this mask from the masks dictionary
        del self.masks[mask_name]

    # -----------------------------------------------------------------

    def __imul__(self, factor):

        """
        This function ...
        :param factor:
        :return:
        """

        # Loop over all currently selected frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Multiplying the " + frame_name + " frame by a factor of " + str(factor))

            # Multiply the frame by the given factor
            self.frames[frame_name] *= factor

        # Return a reference to this instance
        return self

    # -----------------------------------------------------------------

    def __itruediv__(self, factor):

        """
        This function ...
        :param factor:
        :return:
        """

        return self.__idiv__(factor)

    # -----------------------------------------------------------------

    def __idiv__(self, factor):

        """
        This function ...
        :param factor:
        :return:
        """

        # Loop over all currently selected frames
        for frame_name in self.frames:

            # Inform the user
            log.info("Dividing the " + frame_name + " frame by a factor of " + str(factor))

            # Divide the frame by the given factor
            self.frames[frame_name] /= factor

        # Return a reference to this instance
        return self

    # -----------------------------------------------------------------

    def rename_frame(self, old_name, new_name):

        """
        This function renames a frame
        :param old_name:
        :param new_name:
        :return:
        """

        # Remove the frame from the dictionary of frames and re-add it under a different key
        self.frames[new_name] = self.frames.pop(old_name)

    # -----------------------------------------------------------------

    def rename_region(self, old_name, new_name):

        """
        This function renames a region
        :param old_name:
        :param new_name:
        :return:
        """

        # Remove the region of the dictionary of regions and re-add it under a different key
        self.regions[new_name] = self.regions.pop(old_name)

    # -----------------------------------------------------------------

    def rename_mask(self, old_name, new_name):

        """
        This function ...
        :param old_name:
        :param new_name:
        :return:
        """

        # Remove the mask from the dictionary of masks and re-add it under a different key
        self.masks[new_name] = self.masks.pop(old_name)

    # -----------------------------------------------------------------

    def load_frames(self, filename, index=None, name=None, description=None, always_call_first_primary=True, rebin_to_wcs=False, hdulist_index=0):

        """
        This function ...
        :param filename:
        :param index:
        :param name:
        :param description:
        :param always_call_first_primary:
        :param rebin_to_wcs:
        :param hdulist_index:
        :return:
        """

        # Check if the file exists
        if not filesystem.is_file(filename): raise IOError("File " + filename + " does not exist")

        # Show which image we are importing
        log.info("Reading in file " + filename + " ...")

        # Open the HDU list for the FITS file
        hdulist = fits.open(filename)

        # Get the primary HDU
        hdu = hdulist[hdulist_index]

        # Get the image header
        self.original_header = hdu.header

        # Get flattened form of the header
        flattened_header = headers.flattened(self.original_header)

        # Obtain the world coordinate system
        wcs = CoordinateSystem(flattened_header)

        # Obtain the filter for this image
        filter = headers.get_filter(self.name, self.original_header)

        # Inform the user on the filter
        if filter is not None: log.info("The filter for this image is " + filter.filterID())
        else: log.warning("Could not determine the filter for this image")

        # Obtain the units of this image
        unit = headers.get_unit(self.original_header)

        # Get the magnitude zero-point
        zero_point = headers.get_zero_point(self.original_header)

        # Check whether the image is sky-subtracted
        sky_subtracted = headers.is_sky_subtracted(self.original_header)

        # Check whether multiple planes are present in the FITS image
        nframes = headers.get_number_of_frames(self.original_header)
        if nframes > 1:

            # For each frame
            for i in range(nframes):

                # If only a frame with specific index needs to be imported, skip this frame if it does not correspond
                if index is not None and i != index: continue

                # Get name and description of frame
                name, description, plane_type = headers.get_frame_name_and_description(self.original_header, i, always_call_first_primary)

                # The sky-subtracted flag should only be set for the primary frame
                subtracted = sky_subtracted if i == 0 else False

                # Check the shape of this new frame
                if self.shape is not None:

                    if hdu.data[i].shape != self.shape:

                        if rebin_to_wcs:

                            # Inform the user
                            log.warning("Rebinning the " + name + " frame (plane " + str(i) + ") of " + filename + " to match the shape of this image")

                            # Check if the unit is a surface brightness unit
                            if unit != u.Unit("MJy/sr"): raise ValueError("Cannot rebin since unit " + str(unit) + " is not recognized as a surface brightness unit")

                            # Change the data and the WCS
                            hdu.data[i] = transformations.align_and_rebin(hdu.data[i], flattened_header, self.wcs.to_header())
                            wcs = self.wcs

                        else: raise ValueError("The shape of the " + name + " frame (plane " + str(i) + ") of " + filename + " does not match the shape of this image")

                # Add this frame to the frames dictionary
                if plane_type == "frame":

                    # data, wcs=None, name=None, description=None, unit=None, zero_point=None, filter=None, sky_subtracted=False, fwhm=None
                    frame = Frame(hdu.data[i],
                                  wcs=wcs,
                                  name=name,
                                  description=description,
                                  unit=unit,
                                  zero_point=zero_point,
                                  filter=filter,
                                  sky_subtracted=subtracted)
                    self.add_frame(frame, name)

                elif plane_type == "mask":

                    #data, name=None, description=None
                    mask = Mask(hdu.data[i], name=name, description=description)
                    self.add_mask(mask, name)

                else: raise ValueError("Unrecognized type (must be frame or mask)")

        else:

            # Sometimes, the 2D frame is embedded in a 3D array with shape (1, xsize, ysize)
            if len(hdu.data.shape) == 3: hdu.data = hdu.data[0]

            if name is None: name = "primary"
            if description is None: description = "the primary signal map"

            dummy_name, dummy_description, plane_type = headers.get_frame_name_and_description(self.original_header, 0)

            # Check the shape of this new frame
            if self.shape is not None:

                if hdu.data.shape != self.shape:

                    if rebin_to_wcs:

                        # Inform the user
                        log.warning("Rebinning the " + name + " frame (plane 0) of " + filename + " to match the shape of this image")

                        # Check if the unit is a surface brightness unit
                        if unit != u.Unit("MJy/sr"): raise ValueError("Cannot rebin since unit " + str(unit) + " is not recognized as a surface brightness unit")

                        # Change the data and the WCS
                        hdu.data = transformations.align_and_rebin(hdu.data, flattened_header, self.wcs.to_header())
                        wcs = self.wcs

                    else: raise ValueError("The shape of the " + name + " frame (plane 0) of " + filename + " does not match the shape of this image")

            if plane_type == "frame":

                # data, wcs=None, name=None, description=None, unit=None, zero_point=None, filter=None, sky_subtracted=False, fwhm=None
                frame = Frame(hdu.data,
                              wcs=wcs,
                              name=name,
                              description=description,
                              unit=unit,
                              zero_point=zero_point,
                              filter=filter,
                              sky_subtracted=sky_subtracted)
                # Add the primary image frame
                self.add_frame(frame, name)

            elif plane_type == "mask":

                #data, name=None, description=None
                mask = Mask(hdu.data, name=name, description=description)
                # Add the mask
                self.add_mask(mask, name)

            else: raise ValueError("Unrecognized type (must be frame or mask)")

        # Add meta information
        for key in self.original_header: self.metadata[key.lower()] = self.original_header[key]

        # Close the FITS file
        hdulist.close()

    # -----------------------------------------------------------------

    def add_frame(self, frame, name, overwrite=False):

        """
        This function ...
        :param frame:
        :param name:
        :param overwrite:
        :return:
        """

        # Inform the user
        log.info("Adding '" + name + "' to the set of frames ...")

        # Check whether a frame with this name already exists
        if name in self.frames and not overwrite: raise RuntimeError("A frame with this name already exists")

        # Check if the shape matches the shape of this image
        if self.shape is not None:
            if frame.shape != self.shape: raise ValueError("Frame does not have the correct shape for this image")

        # Set the WCS
        if self.wcs is not None: frame.wcs = self.wcs

        # Add the layer to the layers dictionary
        self.frames[name] = frame

    # -----------------------------------------------------------------

    def add_region(self, region, name, overwrite=False):

        """
        This function ...
        :param region:
        :param name:
        :param overwrite:
        :return:
        """

        # Inform the user
        log.info("Adding '" + name + "' to the set of regions ...")

        # Check whether a region with this name already exists
        if name in self.regions and not overwrite: raise RuntimeError("A region with this name already exists")

        # Add the region to the set of regions
        self.regions[name] = region

    # -----------------------------------------------------------------

    def add_mask(self, mask, name, overwrite=False):

        """
        This function ...
        :param mask:
        :param name:
        :param overwrite:
        :return:
        """

        # Inform the user
        log.info("Adding '" + name + "' to the set of masks ...")

        # Check whether a mask with this name already exists
        if name in self.masks and not overwrite: raise RuntimeError("A mask with this name already exists")

        # Check if the shape matches the shape of this image
        if mask.shape != self.shape: raise ValueError("Mask does not have the correct shape for this image")

        # Add the mask to the set of masks
        self.masks[name] = mask

# -----------------------------------------------------------------
