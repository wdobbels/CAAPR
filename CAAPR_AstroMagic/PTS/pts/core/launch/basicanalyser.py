#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.launch.analyser Contains the BasicAnalyser class, used for analysing simulation output.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ..basics.configurable import Configurable
from ..extract.progress import ProgressExtractor
from ..extract.timeline import TimeLineExtractor
from ..extract.memory import MemoryExtractor
from ..plot.progress import ProgressPlotter
from ..plot.timeline import TimeLinePlotter
from ..plot.memory import MemoryPlotter
from ..plot.seds import plotseds
from ..plot.grids import plotgrids
from ..plot.rgbimages import makergbimages
from ..plot.wavemovie import makewavemovie
from ..misc.fluxes import ObservedFluxCalculator
from ..misc.images import ObservedImageMaker
from ..tools.logging import log
from ..tools import filesystem
from ..plot.sed import SEDPlotter
from ...modeling.core.sed import SED, ObservedSED

# -----------------------------------------------------------------

class BasicAnalyser(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(BasicAnalyser, self).__init__(config, "core")

        # -- Attributes --

        # Set the simulation object to None initially
        self.simulation = None

        # The analysis options
        self.extraction_options = None
        self.plotting_options = None
        self.misc_options = None

        # The extractors
        self.progress_extractor = ProgressExtractor()
        self.timeline_extractor = TimeLineExtractor()
        self.memory_extractor = MemoryExtractor()

        # The flux calculator and image maker
        self.flux_calculator = None
        self.image_maker = None

    # -----------------------------------------------------------------

    def run(self, simulation):

        """
        This function ...
        :param simulation
        :return:
        """

        # 1. Call the setup function
        self.setup(simulation)

        # 2. Extract information from the simulation's log files
        self.extract()

        # 3. Make plots based on the simulation output
        self.plot()

        # 4. Miscellaneous output
        self.misc()

    # -----------------------------------------------------------------

    def setup(self, simulation):

        """
        This function ...
        :param simulation:
        :return:
        """

        # Call the setup function of the base class
        super(BasicAnalyser, self).setup()

        # Make a local reference to the simulation object
        self.simulation = simulation

        # Also make references to the simulation's analysis options for extraction, plotting and misc (for shorter notation)
        self.extraction_options = self.simulation.analysis.extraction
        self.plotting_options = self.simulation.analysis.plotting
        self.misc_options = self.simulation.analysis.misc

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Set the simulation to None
        self.simulation = None

        # Set the options to None
        self.extraction_options = None
        self.plotting_options = None
        self.misc_options = None

        # Clear the extractors
        self.progress_extractor.clear()
        self.timeline_extractor.clear()
        self.memory_extractor.clear()

    # -----------------------------------------------------------------

    def extract(self):

        """
        This function ...
        :return:
        """

        # Extract the progress information
        if self.extraction_options.progress: self.extract_progress()

        # Extract the timeline information
        if self.extraction_options.timeline: self.extract_timeline()

        # Extract the memory information
        if self.extraction_options.memory: self.extract_memory()

    # -----------------------------------------------------------------

    def plot(self):

        """
        This function ...
        :return:
        """

        # If requested, plot the SED's
        if self.plotting_options.seds: self.plot_seds()

        # If requested, make plots of the dust grid
        if self.plotting_options.grids: self.plot_grids()

        # If requested, plot the simulation progress as a function of time
        if self.plotting_options.progress: self.plot_progress()

        # If requested, plot a timeline of the different simulation phases
        if self.plotting_options.timeline: self.plot_timeline()

        # If requested, plot the memory usage as a function of time
        if self.plotting_options.memory: self.plot_memory()

    # -----------------------------------------------------------------

    def misc(self):

        """
        This function ...
        :return:
        """

        # If requested, make RGB images of the output FITS files
        if self.misc_options.rgb: self.make_rgb()

        # If requested, make wave movies from the ouput FITS files
        if self.misc_options.wave: self.make_wave()

        # If requested, calculate observed fluxes from the output SEDs
        if self.misc_options.fluxes: self.calculate_observed_fluxes()

        # If requested, create observed imgaes from the output FITS files
        if self.misc_options.images: self.make_observed_images()

    # -----------------------------------------------------------------

    def extract_progress(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Extracting the progress information ...")

        # Determine the path to the progress file
        path = filesystem.join(self.extraction_options.path, "progress.dat")

        # Run the progress extractor
        self.progress_extractor.run(self.simulation, path)

    # -----------------------------------------------------------------

    def extract_timeline(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Extracting the timeline information ...")

        # Determine the path to the timeline file
        path = filesystem.join(self.extraction_options.path, "timeline.dat")

        # Run the timeline extractor
        self.timeline_extractor.run(self.simulation, path)

    # -----------------------------------------------------------------

    def extract_memory(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Extracting the memory information ...")

        # Determine the path to the memory file
        path = filesystem.join(self.extraction_options.path, "memory.dat")

        # Run the memory extractor
        self.memory_extractor.run(self.simulation, path)

    # -----------------------------------------------------------------

    def plot_seds(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting SEDs ...")

        # If the simulated SED must be plotted against a set of reference flux points
        if self.plotting_options.reference_sed is not None:

            # Inform the user
            log.info("Plotting the SED with reference fluxes ...")

            # Create a new SEDPlotter instance
            plotter = SEDPlotter(self.simulation.name)

            # Loop over the simulated SED files and add the SEDs to the SEDPlotter
            for sed_path in self.simulation.seddatpaths():

                # Determine a label for this simulated SED
                sed_label = filesystem.name(sed_path).split("_sed.dat")[0]

                # Load the SED
                sed = SED.from_file(sed_path)

                # Add the simulated SED to the plotter
                plotter.add_modeled_sed(sed, sed_label)

            # Add the reference SED
            reference_sed = ObservedSED.from_file(self.plotting_options.reference_sed)
            plotter.add_observed_sed(reference_sed, "observation")

            # Determine the path to the plot file
            path = filesystem.join(self.plotting_options.path, "sed." + self.plotting_options.format)
            plotter.run(path)

        # Use the simple plotseds function
        else: plotseds(self.simulation, output_path=self.plotting_options.path, format=self.plotting_options.format)

    # -----------------------------------------------------------------

    def plot_grids(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting grids ...")

        # Plot the dust grid for the simulation
        plotgrids(self.simulation, output_path=self.plotting_options.path)

    # -----------------------------------------------------------------

    def plot_progress(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting the progress information ...")

        # Create and run a ProgressPlotter object
        plotter = ProgressPlotter()
        plotter.run(self.progress_extractor.table, self.plotting_options.path)

    # -----------------------------------------------------------------

    def plot_timeline(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting the timeline ...")

        # Create and run a TimeLinePlotter object
        plotter = TimeLinePlotter()
        plotter.run(self.timeline_extractor.table, self.plotting_options.path)

    # -----------------------------------------------------------------

    def plot_memory(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting the memory information ...")

        # Create and run a MemoryPlotter object
        plotter = MemoryPlotter()
        plotter.run(self.memory_extractor.table, self.plotting_options.path)

    # -----------------------------------------------------------------

    def make_rgb(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making RGB images ...")

        # Make RGB images from the output images
        makergbimages(self.simulation, output_path=self.misc_options.path)

    # -----------------------------------------------------------------

    def make_wave(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making wave movies ...")

        # Make wave movies from the output images
        makewavemovie(self.simulation, output_path=self.misc_options.path)

    # -----------------------------------------------------------------

    def calculate_observed_fluxes(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the observed fluxes ...")

        # Create and run a ObservedFluxCalculator object
        self.flux_calculator = ObservedFluxCalculator()
        self.flux_calculator.run(self.simulation, output_path=self.misc_options.path, filter_names=self.misc_options.observation_filters)

    # -----------------------------------------------------------------

    def make_observed_images(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making the observed images ...")

        # Create and run an ObservedImageMaker object
        self.image_maker = ObservedImageMaker()
        self.image_maker.run(self.simulation, output_path=self.misc_options.path, filter_names=self.misc_options.observation_filters)

# -----------------------------------------------------------------
