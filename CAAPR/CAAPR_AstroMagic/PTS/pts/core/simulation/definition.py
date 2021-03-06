#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.simulation.definition Contains the SingleSimulationDefinition and MultiSimulationDefinition classes.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# -----------------------------------------------------------------

class SingleSimulationDefinition(object):

    """
    This class ...
    """

    def __init__(self, ski_path, input_path, output_path, name=None):

        """
        The constructor ...
        :param ski_path:
        :param input_path:
        :param output_path:
        :param name:
        :return:
        """
        
        # Options for the ski file pattern
        self.ski_path = ski_path

        # The input and output paths
        self.input_path = input_path
        self.output_path = output_path

        # A name for this simulation
        self.name = name
            
    # -----------------------------------------------------------------

    def __str__(self):

        """
        This function ...
        """

        properties = []
        properties.append("ski path: " + self.ski_path)
        properties.append("input path: " + str(self.input_path))
        properties.append("output path: " + str(self.output_path))
    
        return_str = self.__class__.__name__ + ":\n"
        for property in properties: return_str += " -" + property + "\n"
        return return_str

        # -----------------------------------------------------------------

    def __repr__(self):

        """
        This function ...
        """

        return '<' + self.__class__.__name__ + " ski path: '" + self.ski_path + "'>"

# -----------------------------------------------------------------

class MultiSimulationDefinition(object):

    """
    This class ...
    """

    def __init__(self, base_path, pattern, input_name, output_name, recursive=True):

        """
        The constructor ...
        """

        self.base_path = base_path
        self.pattern = pattern
        self.input = input_name
        self.output = output_name
        self.recursive = recursive

# -----------------------------------------------------------------
