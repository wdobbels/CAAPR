#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.train.verification Contains the Verifier class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import os

# Import the relevant PTS classes and modules
from .classification import Classifier
from ...core.basics.configurable import OldConfigurable
from ..core.image import Image
from ..core.source import Source
from ...core.tools import introspection
from ...core.tools import filesystem as fs

# -----------------------------------------------------------------

class Verifier(OldConfigurable):

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
        super(Verifier, self).__init__(config, "magic")

        # The classifier object
        self.classifier = None

        # Determine the path to the magic/classification user directory
        self.classification_user_path = os.path.join(introspection.pts_user_dir, "magic", "classification")

    # -----------------------------------------------------------------

    @classmethod
    def from_arguments(cls, arguments):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Create a new Verifier instance
        verifier = cls()

        # -- Adjust the configuration settings according to the command-line arguments --

        verifier.config.mode = arguments.mode

        # Return the classifier
        return verifier
        
    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # Classify
        self.classify()

        # 2. Verify
        self.verify()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup of the base class
        super(Verifier, self).setup()

        self.classifier = Classifier()
        self.classifier.config.mode = self.config.mode
        
    # -----------------------------------------------------------------

    def classify(self):

        """
        This function ...
        :return:
        """

        self.classifier.run()

    # -----------------------------------------------------------------

    def verify(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Starting the verification ...")

        # Get a list of the filepaths for every FITS file in the current working directory
        file_paths = fs.files_in_path(os.getcwd(), extension="fits", contains=self.config.mode)

        # Keep track of how many files have been processed
        self.number_of_files = len(file_paths)
        self.processed = 0

        # Loop over all FITS files found in the current directory
        for file_path in file_paths:

            # Get information
            name = os.path.basename(file_path).split(".fits")[0]
            info, index = name.split("_")

            # Open the image, select all frames
            image = Image.from_file(file_path, always_call_first_primary=False)
            image.frames.select_all()

            # Create a source
            source = Source.from_image(image)

            is_star = self.classifier.is_star(source)

            label = "star" if is_star else "not a star"

            source.plot(title="Classified as: " + label)

# -----------------------------------------------------------------
