#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.extract.timeline Contains the TimeLineTable and TimeLineExtractor classes. The latter class is used
#  for extracting timeline information from a simulation's log files to a TimeLineTable object.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from datetime import datetime

# Import astronomical modules
from ..tools import tables
from astropy.table import Table
from astropy.utils import lazyproperty

# -----------------------------------------------------------------

class TimeLineTable(Table):

    """
    This function ...
    """

    @classmethod
    def from_columns(cls, process_list, phase_list, start_list, end_list):

        """
        This function ...
        :param process_list:
        :param phase_list:
        :param start_list:
        :param end_list:
        :return:
        """

        names = ["Process rank", "Simulation phase", "Start time", "End time"]
        data = [process_list, phase_list, start_list, end_list]

        # Call the constructor of the base class
        table = cls(data, names=names, masked=True)

        # Set the column units
        table["Start time"].unit = "s"
        table["End time"].unit = "s"

        # The path to the table file
        table.path = None

        # Return the table
        return table

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Open the table
        table = cls.read(path, format="ascii.ecsv")

        # Set the path
        table.path = path

        # Return the table
        return table

    # -----------------------------------------------------------------

    @lazyproperty
    def processes(self):

        """
        This function ...
        :return:
        """

        return max(self["Process rank"]) + 1

    # -----------------------------------------------------------------

    def duration(self, phase, single=False):

        """
        This function ...
        :param phase:
        :param single:
        :return:
        """

        # Keep track of the total amount of time spent in the specified phase
        total = 0.0

        assert self["Process rank"][0] == 0

        # Loop over the table rows
        for i in range(len(self)):

            # Only add the contributions from the root process
            if self["Process rank"][i] > 0: break

            # Check whether the current entry corresponds to the desired phase
            if self["Simulation phase"][i] == phase:

                # Get the start and end time for the phase
                start = self["Start time"][i]
                end = self["End time"][i]

                # Calculate the time duration for this phase, returning it if single=True, otherwise add it to the total
                if single: return end - start
                else: total += end - start

        # Return the total amount of time spent in the specified phase
        return total

    # -----------------------------------------------------------------

    def duration_without(self, phases):

        """
        This function ...
        :param phases:
        :return:
        """

        # If no phases are given, set an empty list
        if phases is None: phases = []

        # Create a list of phases is only one is given
        if isinstance(phases, basestring): phases = [phases]

        # Keep track of the total amount of time spent in phases other than the specified phase
        total = 0.0

        assert self["Process rank"][0] == 0

        # Loop over the table rows
        for i in range(len(self)):

            # Only add the contributions from the root process
            if self["Process rank"][i] > 0: break

            # Check whether the current entry corresponds to a phase different from the specified phase
            if self["Simulation phase"][i] not in phases:

                # Get the start and end time for this phase
                start = self["Start time"][i]
                end = self["End time"][i]

                # Add the duration to the total
                total += end - start

        # Return the total amount of time spent in phases other than the specified phase
        return total

    # -----------------------------------------------------------------

    @lazyproperty
    def total(self):

        """
        This function ...
        :return:
        """

        return self.duration_without(None)

    # -----------------------------------------------------------------

    @lazyproperty
    def setup(self):

        """
        This function ...
        :return:
        """

        return self.duration("setup")

    # -----------------------------------------------------------------

    @lazyproperty
    def stellar(self):

        """
        This function ...
        :return:
        """

        return self.duration("stellar", single=True)

    # -----------------------------------------------------------------

    @lazyproperty
    def spectra(self):

        """
        This function ...
        :return:
        """

        return self.duration("spectra")

    # -----------------------------------------------------------------

    @lazyproperty
    def dust(self):

        """
        This function ...
        :return:
        """

        return self.duration("dust")

    # -----------------------------------------------------------------

    @lazyproperty
    def dustem(self):

        """
        This function ...
        :return:
        """

        # Loop over the table rows in opposite direction so that we know the first dust photon shooting phase is the
        # final dust emission phase
        for i in reversed(range(len(self))):

            # Only add the contributions from the root process
            if self["Process rank"][i] > 0: break

            # Check whether the current entry corresponds to the desired phase
            if self["Simulation phase"][i] == "dust":

                # Get the start and end time for the phase
                start = self["Start time"][i]
                end = self["End time"][i]

                # Calculate the time duration for the dust emission phase (only the shooting part)
                return end - start

    # -----------------------------------------------------------------

    @lazyproperty
    def writing(self):

        """
        This function ....
        :return:
        """

        return self.duration("write")

    # -----------------------------------------------------------------

    @lazyproperty
    def communication(self):

        """
        This function ...
        :return:
        """

        return self.duration("comm")

    # -----------------------------------------------------------------

    @lazyproperty
    def waiting(self):

        """
        This function ...
        :return:
        """

        return self.duration("wait")

    # -----------------------------------------------------------------

    @lazyproperty
    def other(self):

        """
        This function ...
        :return:
        """

        return self.duration(None)

    # -----------------------------------------------------------------

    @lazyproperty
    def serial(self):

        """
        This function ...
        :return:
        """

        return self.setup + self.writing + self.other

    # -----------------------------------------------------------------

    @lazyproperty
    def parallel(self):

        """
        This function ...
        :return:
        """

        return self.stellar + self.spectra + self.dust

    # -----------------------------------------------------------------

    @lazyproperty
    def overhead(self):

        """
        This function ...
        :return:
        """

        return self.communication + self.waiting

    # -----------------------------------------------------------------

    def save(self):

        """
        This function ...
        :return:
        """

        # Save to the current path
        self.saveto(self.path)

    # -----------------------------------------------------------------

    def saveto(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Write the table in ECSV format
        self.write(path, format="ascii.ecsv")

        # Set the path
        self.path = path

# -----------------------------------------------------------------

class TimeLineExtractor(object):

    """
    This class ...
    """

    def __init__(self):

        """
        The constructor ...
        :return:
        """

        # -- Attributes --

        # The list of log files created by the simulation
        self.log_files = None

        # The table containing the timeline information
        self.table = None

    # -----------------------------------------------------------------

    def run(self, simulation, output_path=None):

        """
        This function ...
        :param simulation:
        :param output_path:
        :return:
        """

        # Obtain the log files created by the simulation
        self.log_files = simulation.logfiles()

        # Perform the extraction
        self.extract()

        # Write the results
        if output_path is not None: self.write(output_path)

        # Return the timeline table
        return self.table

    # -----------------------------------------------------------------

    def extract(self):

        """
        This function ...
        :return:
        """

        # Initialize lists for the columns
        process_list = []
        phase_list = []
        start_list = []
        end_list = []

        # Loop over all log files to determine the earliest recorded time
        t_0 = datetime.now()
        for log_file in self.log_files:
            if log_file.t_0 < t_0: t_0 = log_file.t_0

        # Loop over the log files again and fill the column lists
        unique_processes = []
        for log_file in self.log_files:

            # Get the process rank associated with this log file
            process = log_file.process
            unique_processes.append(process)

            # Keep track of the current phase while looping over the log file entries
            current_phase = log_file.contents["Phase"][0]
            process_list.append(process)
            phase_list.append(current_phase)
            start_list.append((log_file.t_0 - t_0).total_seconds())

            # Loop over all log file entries
            for j in range(len(log_file.contents)):

                # Get the description of the current simulation phase
                phase = log_file.contents["Phase"][j]

                # If a new phase is entered
                if phase != current_phase:

                    # Determine the current time
                    seconds = (log_file.contents["Time"][j] - t_0).total_seconds()

                    # Mark the end of the previous phase
                    end_list.append(seconds)

                    # Mark the start of the current phase
                    process_list.append(process)
                    phase_list.append(phase)
                    start_list.append(seconds)

                    # Update the current phase
                    current_phase = phase

            # Add the last recorded time in the log file as the end of the last simulation phase
            end_list.append((log_file.t_last - t_0).total_seconds())

        # Fix for when the number of phases does not correspond between the different processes
        if len(unique_processes) > 1: verify_phases(process_list, phase_list, start_list, end_list)

        # Create the table
        self.table = TimeLineTable.from_columns(process_list, phase_list, start_list, end_list)

    # -----------------------------------------------------------------

    def write(self, output_path):

        """
        This function ...
        :param output_path:
        :return:
        """

        # Write the table to file
        tables.write(self.table, output_path)

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Set the table to None
        self.table = None

# -----------------------------------------------------------------

def verify_phases(process_list, phase_list, start_list, end_list):

    """
    This function ...
    :param process_list:
    :param phase_list:
    :param start_list:
    :param end_list:
    :return:
    """

    # TODO: right now, it does not fix everything ! only the case where the root process misses a phase at the end compared to the other processes

    # Get the number of processes
    nprocs = max(process_list) + 1

    # For each process rank, get the index in the columns where the entries of that process start
    process_indices = [None] * nprocs
    previous_process = -1
    for i in range(len(process_list)):
        if process_list[i] == previous_process: continue
        else:
            process_indices[process_list[i]] = i
            previous_process = process_list[i]
            if previous_process == nprocs - 1: break

    max_number_of_entries = max([process_indices[i+1]-process_indices[i] for i in range(len(process_indices)-1)])

    for entry_index in range(max_number_of_entries):

        # Check whether the phases correspond and if the process ranks are actually the ranks we loop over below
        phase_process_0 = phase_list[entry_index]
        if process_list[entry_index] != 0: # but already an entry of process rank 1
            if process_list[entry_index] != 1: raise RuntimeError("I don't know how to solve this inconsistent set of columns")

            missing_phase = phase_list[process_indices[1]+entry_index]
            missing_end = end_list[process_indices[1]+entry_index]

            process_list.insert(entry_index, 0)
            phase_list.insert(entry_index, missing_phase)
            start_list.insert(entry_index, end_list[entry_index-1])
            end_list.insert(entry_index, missing_end)

        #for rank in range(1,nprocs):

            #print(phase_process_0, phase_list[process_indices[rank]+entry_index])
            #print(rank, process_list[process_indices[rank]+entry_index])

# -----------------------------------------------------------------
