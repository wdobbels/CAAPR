#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.configuration Provides convenient functions for creating, reading and writing configuration
#  settings files.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import io
import inspect
from config import Config, Mapping

# Import the relevant PTS classes and modules
from . import introspection
from . import filesystem as fs

# -----------------------------------------------------------------

def from_string(string):

    """
    This function ...
    :param string:
    :return:
    """

    string = string.replace(',', '\n')
    fh = io.StringIO(string.decode('unicode-escape'))
    return Config(fh)

# -----------------------------------------------------------------

def special(self, item):

    """
    This function ...
    :param item:
    :return:
    """

    try:
        return self.__getitem__(item)
    except AttributeError:
        self[item] = Mapping()
        return self[item]

# Replace the __getattr__ function
Config.__getattr__ = special
Mapping.__getattr__ = special

# -----------------------------------------------------------------

def new():

    """
    This function ...
    :return:
    """

    return Config()

# -----------------------------------------------------------------

def set(subpackage_name, class_name, config=None):

    """
    This function ...
    :param subpackage_name:
    :param class_name:
    :param config:
    :return:
    """

    # Determine the path to the default configuration file
    subpackage_directory = os.path.join(inspect.getfile(inspect.currentframe()).split("/core")[0], subpackage_name)
    default_config = os.path.join(subpackage_directory, "config", class_name + ".cfg")

    # If we have not created a default configuration file for this class yet ...
    if not fs.is_file(default_config): default_config = os.path.join(introspection.pts_package_dir, "core", "config", "default.cfg")

    # Open the default configuration if no configuration file is specified, otherwise adjust the default
    # settings according to the user defined configuration file
    if config is None: return open(default_config)
    else: return open(config, default_config)

# -----------------------------------------------------------------

def open(config, default_config=None):

    """
    This function ...
    :param config:
    :param default_config:
    :return:
    """

    # Open the config file
    if isinstance(config, basestring): config = Config(file(config))

    # If a default configuration file is not given, return the opened config file
    if default_config is None: return config
    else:

        # Open the default config file
        if isinstance(default_config, basestring): default_config = Config(file(default_config))

        # Adjust the default configuration according to the user-defined configuration
        adjust(default_config, config)

        # Return the adjusted default configuration
        return default_config

# -----------------------------------------------------------------

def adjust(config, user_config):

    """
    This function ...
    :param config:
    :param user_config:
    :return:
    """

    # Loop over all keys in the configuration
    for key in user_config:

        # If the property is a mapping (consists of more properties), call this function recursively
        if isinstance(user_config[key], Mapping):

            # If the Mapping with the name key does not exist in the config, add an empty mapping
            if not key in config: config[key] = Mapping()

            adjust(config[key], user_config[key])

        # Adapt the value of the property in the configuration to be equal to the value in the user configuration
        else: config[key] = user_config[key]

# -----------------------------------------------------------------
