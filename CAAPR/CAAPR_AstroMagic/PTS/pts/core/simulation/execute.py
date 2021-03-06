#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.simulation.execute Executing the SKIRT command line application
#
# An instance of the SkirtExec class in this module represents a particular SKIRT executable,
# and allows invoking it with given command line arguments.

# -----------------------------------------------------------------

# Import standard modules
import os
import subprocess

# Import the relevant PTS classes and modules
from .arguments import SkirtArguments
from ..tools import introspection
from ..tools import filesystem as fs
from ..tools.logging import log

# -----------------------------------------------------------------
#  SkirtExec class
# -----------------------------------------------------------------

## An instance of the SkirtExec class represents a particular SKIRT executable, and allows invoking it with
# given command line arguments. The current implementation only supports local execution; remote execution
# on another host will be added in the future.
class SkirtExec:

    ## The constructor accepts a single argument specifying the path to the <tt>SKIRT</tt> executable to be used.
    # - The path may or may not include the "skirt" filename and if not, it may or may not include the final "/" of a
    #   directory path. The path may be absolute, relative to a user's home folder, or relative to the current
    #   working directory.
    #   The default value is the empty path, which means <tt>SKIRT</tt> is looked for in the standard system path \c $PATH.
    # - mpistyle: the method or style to invoke the mpirun command; currently supported values are 'generic' (the
    #   default), which uses the standard -np switch useful for launching a number of MPI processes on a single
    #   computing node, and 'lsf', which uses the -lsf switch supported by platform MPI under the LSF cluster queueing
    #   system.
    def __init__(self, path="", mpi_style="generic"):

        # Set the SKIRT path
        self._path = path if path is not None else ""
        if not self._path.endswith("skirt"): self._path = os.path.join(self._path, "skirt")
        if self._path != "skirt": self._path = os.path.realpath(os.path.expanduser(self._path))

        if self._path == "skirt":

            if introspection.skirt_is_present(): self._path = introspection.skirt_path
            else: raise EnvironmentError("SKIRT is not installed or not in the PATH environment variable")

        # Indicate no simulations are running yet
        self._process = None

        # Set the MPI style
        self.mpi_style = mpi_style.lower()

    ## This function invokes the <tt>SKIRT</tt> executable with the simulations and command line options corresponding to the
    #  values of the function arguments:
    #
    # - simulations: the list of simulations (instances of SkirtSimulation) to be executed
    # - recursive: if one or more simulations passed to the execute function contain wildcards in their \em ski file
    #   path, the recursive argument can be used to specify whether all directories recursively nested within the base
    #   path are searched as well, using the same filename pattern.
    # - inpath: a string specifying the absolute or relative path for simulation input files.
    # - outpath: a string specifying the absolute or relative path for simulation output files.
    # - skirel: if \c True, the simulation input/output paths are relative to the \em ski file being processed;
    #   if \c False or missing, they are relative to the current directory.
    # - threads: a positive integer specifying the number of parallel threads for each simulation; if zero or missing
    #   the number of logical cores on the computer is used.
    # - parallel: a positive integer specifying the number of simulations to be executed in parallel (by means of
    #   multithreading); if missing the default value is one.
    # - processes: the number of parallel MPI processes to be launched. The default value is one, which means MPI
    #   is not used. If the specified number of processes is larger than one, the value of \em parallel argument is
    #   ignored (i.e. you can't run multiple simulations in parallel when using MPI).
    # - verbose: This option has effect only if the number of processes is larger than one. If set to \c True, each
    #   process creates its own complete log file. If missing or set to \em False, only the root process creates a
    #   full log file, and the other processes only create a log file when there are errors or warnings.
    # - memory: This option enables memory logging for SKIRT.
    # - allocation: This option enables memory allocation logging for SKIRT.
    # - emulate: This option can be switched on to run SKIRT in 'emulation' mode to estimate the memory consumption.
    # - single: if \c True, only a single simulation is expected from the passed ski pattern, and the function returns
    #   a single SkirtSimulation object instead of a list.
    # - wait: if \c True or missing, the function waits until <tt>SKIRT</tt> execution completes and sends the brief
    #   SKIRT log to the standard console; if \c False the function returns immediately without waiting for SKIRT,
    #   and SKIRT's log messages are sent to the null device.
    # - silent: if \c True or missing, the SKIRT output will not be visible on the console.
    #
    # The function returns a list of SkirtSimulation instances corresponding to the simulations to be performed
    # (after processing any wildcards in the ski filenames), in arbitrary order.
    #
    def execute(self, skipattern, recursive=False, inpath=None, outpath=None, skirel=False, threads=0, parallel=1,
                processes=1, mpistyle='generic', brief=False, verbose=False, memory=False, allocation=False,
                emulate=False, single=False, wait=True, silent=False):

        self.mpi_style = mpistyle

        # Create a SkirtArguments object
        arguments = SkirtArguments()

        # The ski file pattern
        arguments.ski_pattern = skipattern
        arguments.recursive = recursive
        arguments.relative = skirel

        # Input and output
        arguments.input_path = inpath
        arguments.output_path = outpath

        # Parallelization settings
        arguments.parallel.threads = threads
        arguments.parallel.processes = processes
        arguments.parallel.simulations = parallel

        # Logging settings
        arguments.logging.brief = brief
        arguments.logging.verbose = verbose
        arguments.logging.memory = memory
        arguments.logging.allocation = allocation

        # Other settings
        arguments.emulate = emulate
        arguments.single = single

        # Run SKIRT with the specified parameters
        return self.run(arguments, wait, silent)

    ## This function does the same as the execute function, but obtains its arguments from a SkirtArguments object
    def run(self, arguments, wait=True, silent=False):

        # Check whether MPI is present on this system if multiple processe are requested
        if arguments.parallel.processes > 1 and not introspection.has_mpi():
            log.warning("No mpirun executable: skipping simulations")
            return []

        # Determine the MPI command
        if self.mpi_style == "lsf":
            scheduler = True
            mpi_command = "mpirun -lsf"
        elif self.mpi_style == "generic":
            scheduler = False
            mpi_command = "mpirun"
        else: raise ValueError("Invalid MPI style")

        # Get the command string
        command = arguments.to_command(self._path, mpi_command, scheduler)

        # Launch the SKIRT command
        if wait:
            self._process = None
            if silent: subprocess.call(command, stdout=open(os.devnull,'w'), stderr=open(os.devnull,'w'))
            else: subprocess.call(command)
        else: self._process = subprocess.Popen(command, stdout=open(os.path.devnull, 'w'), stderr=subprocess.STDOUT)

        # Return the list of simulations so that their results can be followed up
        return arguments.simulations()

    ## This function returns True if the previously started SKIRT process is still running, False otherwise
    def isrunning(self):
        return (self._process != None and self._process.poll() == None)

    ## This function waits for the previously started SKIRT process to complete, if needed
    def wait(self):
        if self.isrunning(): self._process.wait()

    ## This function returns a string with version information on the SKIRT executable represented by this
    # object. The function invokes SKIRT with an incorrect command line argument to obtain this information.
    def version(self):
        # execute skirt with incorrect argument list and get its output
        process = subprocess.Popen([self._path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = process.communicate()[0]

        # return the relevant portion of the output
        return "SKIRT" + output.splitlines()[0].partition("SKIRT")[2]

    ## This function returns a string with the path of the SKIRT directory that is used, for example: HOME/SKIRT
    @property
    def root_directory(self):
        return os.path.dirname(os.path.dirname(os.path.dirname(self._path)))

    ## This function returns the path to the SKIRT repository directory (SKIRT/git)
    @property
    def repo_directory(self):
        return os.path.join(self.root_directory, "git")

    ## This function returns the path to the SKIRT run directory (SKIRT/run)
    @property
    def run_directory(self):
        return os.path.join(self.root_directory, "run")

    ## This function installs SKIRT
    def install(self, private=False):

        # Determine the path to the home directory
        home_dir = os.path.expanduser("~")

        # Create the SKIRT directory
        root_dir = os.path.join(home_dir, "SKIRT")
        os.mkdir(root_dir)

        # Create the SKIRT run, git and release directories
        run_dir = os.path.join(root_dir, "run")
        repo_dir = os.path.join(root_dir, "git")
        release_dir = os.path.join(root_dir, "release")
        fs.create_directories(run_dir, repo_dir, release_dir)

        #  Clone the SKIRT repository
        if private: subprocess.call("git clone git@github.ugent.be:SKIRT/SKIRT.git git", cwd=root_dir)

        else: subprocess.call("git clone https://github.com/SKIRT/SKIRT.git git", cwd=root_dir)

        # Compile the SKIRT code
        subprocess.call("./makeSKIRT.sh", cwd=repo_dir)

        # Put SKIRT in the PATH environment variable
        # ...

# -----------------------------------------------------------------
