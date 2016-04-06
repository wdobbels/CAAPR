#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.basics.remote Contains the Remote class.

# -----------------------------------------------------------------

# Import standard modules
import os
import re
import sys
import pxssh
import pexpect
import tempfile

# Import the relevant PTS classes and modules
from .host import Host
from ..tools.logging import log

# -----------------------------------------------------------------

class Remote(object):

    """
    This function ...
    """

    def __init__(self):

        """
        The constructor ...
        :return:
        """

        # Call the constructor of the base class
        super(Remote, self).__init__()

        # -- Attributes --

        # The SSH interface, an instance of the pxssh class
        self.ssh = pxssh.pxssh()

        # The host instance
        self.host = None

        # A flag indicating whether the connection with the remote has been established
        self.connected = False

        # A regular expression object that strips away special unicode characters, used on the remote console output
        self.ansi_escape = re.compile(r'\x1b[^m]*m')

    # -----------------------------------------------------------------

    def setup(self, host_id, cluster=None):

        """
        This function ...
        :param host_id:
        :param cluster:
        :return:
        """

        # Create the host object
        self.host = Host(host_id, cluster)

        # Make the connection
        self.login()

        # Load the necessary modules
        if self.host.modules is not None:

            log.info("Loading necessary modules...")
            self.execute("module load " + " ".join(self.host.modules), output=False)

        # Check whether the output directory exists
        if not self.is_directory(self.host.output_path): raise ValueError("The specified output path does not exist")

    # -----------------------------------------------------------------

    def __del__(self):

        """
        The destructor ...
        :return:
        """

        # Disconnect from the remote host
        self.logout()

    # -----------------------------------------------------------------

    def login(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Logging in to the remote environment on host '" + self.host.id + "' ...")

        # Connect to the remote host
        self.connected = self.ssh.login(self.host.name, self.host.user, self.host.password)

        # Check whether connection was succesful
        if not self.connected: raise RuntimeError("Connection failed")

    # -----------------------------------------------------------------

    def logout(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Logging out from the remote environment ...")

        # Disconnect
        if self.connected: self.ssh.logout()

    # -----------------------------------------------------------------

    def start_screen(self, name, local_script_path, script_destination, screen_output_path=None):

        """
        This function ...
        :param name:
        :param local_script_path:
        :param script_destination:
        :param screen_output_path:
        :return:
        """

        # Copy the script to the remote host
        self.upload(local_script_path, script_destination)

        # Rename the remote script
        local_script_name = os.path.basename(local_script_path)
        remote_script_name = name + ".sh"
        remote_script_path = os.path.join(script_destination, remote_script_name)
        self.rename_file(script_destination, local_script_name, remote_script_name)

        # Make the shell script executable
        self.execute("chmod +x " + remote_script_path, output=False)

        # Record the screen output: 'script' command
        if screen_output_path is not None: self.execute("script " + screen_output_path)

        # Create the screen session and execute the batch script
        self.execute("screen -S " + name + " -d -m " + remote_script_path, output=False)

        # Remove the remote shell script
        self.execute("rm " + remote_script_path, output=False)

    # -----------------------------------------------------------------

    def kill_screen(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        # Quit the specified screen session
        self.execute("screen -S " + name + " -X quit", output=False)

    # -----------------------------------------------------------------

    def kill_job(self, id):

        """
        This function ...
        :param id:
        :return:
        """

        # Stop the job with the specified ID
        self.execute("qdel " + str(id), output=False)

    # -----------------------------------------------------------------

    def screen_state(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        # Execute the 'screen -ls' command
        output = self.execute("screen -ls")

        # Loop over the different active screen sessions
        for entry in output:

            # Check if the specified screen name corresponds to the current entry
            if name in entry:

                # Check the state of this screen session
                if "Detached" in entry: return "detached"
                elif "Attached" in entry: return "attached"
                else: raise ValueError("Screen " + name + " in unkown state")

        # If the screen name was not encountered, return None (the screen session has finished or has been aborted)
        return None

    # -----------------------------------------------------------------

    def is_active_screen(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        state = self.screen_state(name)
        return state == "detached" or state == "attached"

    # -----------------------------------------------------------------

    def is_attached_screen(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        return self.screen_state(name) == "attached"

    # -----------------------------------------------------------------

    def is_detached_screen(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        return self.screen_state(name) == "detached"

    # -----------------------------------------------------------------

    def get_requirements(self, processors):

        """
        This function calculates the required amount of nodes and processors per node, given a certain number of
        processors.
        :param processors:
        :return:
        """

        # Calculate the necessary amount of nodes
        nodes = processors // self.cores + (processors % self.cores > 0)

        # Determine the number of processors per node
        ppn = processors if nodes == 1 else self.cores

        # Return the number of nodes and processors per node
        return nodes, ppn

    # -----------------------------------------------------------------

    def execute(self, command, output=True, expect_eof=True, contains_extra_eof=False, show_output=False, timeout=None):

        """
        This function ...
        :param command:
        :param output:
        :param expect_eof:
        :param contains_extra_eof:
        :param show_output:
        :param timeout:
        :return:
        """

        # Send the command
        self.ssh.sendline(command)

        # If the output has to be shown on the console, set the 'logfile' to the standard system output stream
        # Otherwise, assure that the logfile is set to 'None'
        if show_output: self.ssh.logfile = sys.stdout
        else: self.ssh.logfile = None

        # Retrieve the output if requested
        eof = self.ssh.prompt(timeout=timeout)

        # If an extra EOF is used before the actual output line (don't ask me why but I encounter this on the HPC UGent infrastructure), do prompt() again
        if contains_extra_eof: eof = self.ssh.prompt()

        # If the command could not be sent, raise an error
        if not eof and expect_eof and not contains_extra_eof: raise RuntimeError("The command could not be sent")

        # Set the log file back to 'None'
        self.ssh.logfile = None

        # Ignore the first and the last line (the first is the command itself, the last is always empty)
        if output:
            # Trial and error to get it right for HPC UGent login nodes; don't know what is happening
            if contains_extra_eof: return self.ssh.before.replace('\x1b[K', '').split("\r\n")[1:-1]
            else: return self.ansi_escape.sub('', self.ssh.before).replace('\x1b[K', '').split("\r\n")[1:-1]

    # -----------------------------------------------------------------

    def execute_python_interactive(self, lines, show_output=False):

        """
        This function ...
        :param lines:
        :param show_output:
        :return:
        """

        # Initiate a remote interactive python session
        self.execute("python", expect_eof=False, show_output=show_output)

        # Inject each line into the remote python prompt
        for line in lines: self.execute(line, expect_eof=False, show_output=show_output)

        # Close the remote python session
        self.execute("exit()")

    # -----------------------------------------------------------------

    def execute_python_script(self, script_path, show_output=False):

        """
        This function ...
        :param script_path:
        :param show_output:
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def rename_file(self, directory, old_name, new_name):

        """
        This function ...
        :param directory:
        :param old_name:
        :param new_name:
        :return:
        """

        # Determine the old and new file path
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)

        # Use the 'mv' command to rename the file
        self.execute("mv " + old_path + " " + new_path)

    # -----------------------------------------------------------------

    def remove_directory(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        self.execute("rm -rf " + path, output=False)

    # -----------------------------------------------------------------

    def remove_file(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        self.execute("rm " + path, output=False)

    # -----------------------------------------------------------------

    def change_cwd(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        self.execute("cd " + path)

    # -----------------------------------------------------------------

    def directories_in_path(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Get the path to the current working directory
        working_directory = self.working_directory

        # Change the working directory to the provided path
        self.change_cwd(path)

        # List the directories in the provided path
        output = self.execute("for i in $(ls -d */); do echo ${i%%/}; done")

        # Change the working directory back to the original working directory
        self.change_cwd(working_directory)

        # Return the list of directories
        return output

    # -----------------------------------------------------------------

    def files_in_path(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Get the path to the current working directory
        working_directory = self.working_directory

        # Change the working directory to the provided path
        self.change_cwd(path)

        # List the files in the provided path
        output = self.execute("for f in *; do [[ -d $f ]] || echo $f; done")

        # Change the working directory back to the original working directory
        self.change_cwd(working_directory)

        # Return the list of directories
        return output

    # -----------------------------------------------------------------

    def to_home_directory(self):

        """
        This function ...
        """

        # Navigate to the home directory
        self.execute("cd ~", output=False)

    # -----------------------------------------------------------------

    def create_directory(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Create the remote directory
        self.execute("mkdir " + path, output=False)

    # -----------------------------------------------------------------

    def create_directories(self, paths):

        """
        This function ...
        :return:
        """

        # Create the remote directories
        self.execute("mkdir " + " ".join(paths), output=False)

    # -----------------------------------------------------------------

    def download(self, origin, destination, timeout=30, new_name=None, compress=False, show_output=False):

        """
        This function ...
        :param origin:
        :param destination:
        :param timeout:
        :param new_name:
        :param compress:
        :param show_output:
        :return:
        """

        # Construct the command string
        copy_command = "scp "
        if compress: copy_command += "-C "

        # Add the host address
        copy_command += self.host.user + "@" + self.host.name + ":"

        # If the origin is a string, we assume it represents a single file path or directory path
        if isinstance(origin, basestring):

            # Check if the origin represents a file
            if self.is_file(origin): copy_command += origin.replace(" ", "\ ") + " "

            # Check if it represents a directory
            #elif self.is_directory(origin): copy_command += origin.replace(" ", "\ ") + "/* " + "-r "
            elif self.is_directory(origin): copy_command += origin.replace(" ", "\ ") + "/* "

            # The origin does not exist
            else: raise ValueError("The specified path " + origin + " does not represent an existing directory or file on the remote host")

        # If the origin is a list, we assume it contains multiple file paths
        elif isinstance(origin, list):

            # Check whether the files exist remotely
            for file_path in origin:
                if not self.is_file(file_path): raise ValueError("The file " + file_path + " does not exist on the remote host")

            # Escape possible space characters
            origin = [path.replace(" ", "\ ") for path in origin]

            # Add a quotation mark character because the seperate file paths are going to be separated by spaces
            # (the command is going to be of the form scp username@ip.of.server.copyfrom:"file1.log file2.log" "~/yourpathtocopy")
            copy_command += '"'

            # Add the file paths to the command string
            copy_command += " ".join(origin)

            # Add another quotation mark to identify the end of the filepath list
            copy_command += '" '

        # Add the destination path to the command
        copy_command += destination.replace(" ", "\ ") + "/"
        if new_name is not None: copy_command += new_name

        # Debugging
        log.debug("Copy command: " + copy_command)

        # Create the pexpect child instance
        child = pexpect.spawn(copy_command, timeout=timeout)
        if self.host.password is not None:
            child.expect(['password: '])
            child.sendline(self.host.password)

        # If the output does not have to be shown on the console, create a temporary file where the output is written to
        if not show_output:

            # Temporary file for output of the scp command
            temp_file_path = tempfile.mktemp()
            temp_file = open(temp_file_path, 'w')

        # If the output has to be shown on the console, set the 'logfile' to the standard system output stream
        else: child.logfile = sys.stdout

        # Execute the command and get the output
        child.expect(pexpect.EOF, timeout=None)
        child.close()

        if not show_output:

            # Close the temporary output file
            temp_file.close()

            # Open the output file again and read the contents
            temp_file = open(temp_file_path, 'r')
            stdout = temp_file.read()
            temp_file.close()

            # Raise an error if something went wrong
            if child.exitstatus != 0: raise RuntimeError(stdout)

            # Debugging: show the output of the scp command
            log.debug("Copy stdout: " + str(stdout).replace("\n", " "))

    # -----------------------------------------------------------------

    def upload(self, origin, destination, timeout=30, new_name=None, compress=False, show_output=False):

        """
        This function ...
        :param origin:
        :param destination:
        :param timeout:
        :param new_name:
        :param compress:
        :param show_output:
        :return:
        """

        # Construct the command string
        copy_command = "scp "
        if compress: copy_command += "-C "

        # If the origin is a string, we assume it represents a single file path or directory path
        if isinstance(origin, basestring):

            # Check if the origin represents a file
            if os.path.isfile(origin): copy_command += origin.replace(" ", "\ ") + " "

            # Check if it represents a directory
            elif os.path.isdir(origin): copy_command += "-r " + origin.replace(" ", "\ ") + "/ "

            # The origin does not exist
            else: raise ValueError("The specified path " + origin + " does not represent an existing directory or file")

        # If the origin is a list, we assume it contains multiple file paths
        elif isinstance(origin, list):

            # Check whether the files exist locally
            for file_path in origin:
                if not os.path.isfile(file_path): raise ValueError("The file " + file_path + " does not exist")

            # Escape possible space characters
            origin = [path.replace(" ", "\ ") for path in origin]

            # Add the file paths to the command string
            copy_command += " ".join(origin) + " "

        # Invalid argument
        else: raise ValueError("The origin must be a string or a list of strings")

        # Add the host address and the destination directory
        copy_command += self.host.user + "@" + self.host.name + ":" + destination.replace(" ", "\ ") + "/"
        if new_name is not None: copy_command += new_name

        # Debugging
        log.debug("Copy command: " + copy_command)

        # Create the pexpect child instance
        child = pexpect.spawn(copy_command, timeout=timeout)
        if self.host.password is not None:
            child.expect(['password: '])
            child.sendline(self.host.password)

        # If the output does not have to be shown on the console, create a temporary file where the output is written to
        if not show_output:

            # Temporary file for output of the scp command
            temp_file_path = tempfile.mktemp()
            temp_file = open(temp_file_path, 'w')

            child.logfile = temp_file

        # If the output has to be shown on the console, set the 'logfile' to the standard system output stream
        else: child.logfile = sys.stdout

        # Execute the command and get the output
        try:
            child.expect(pexpect.EOF, timeout=None)
        except pexpect.EOF:
            pass
        child.close()

        if not show_output:

            # Close the temporary output file
            temp_file.close()

            # Open the output file again and read the contents
            temp_file = open(temp_file_path, 'r')
            stdout = temp_file.read()
            temp_file.close()

            # Raise an error if something went wrong
            if child.exitstatus != 0: raise RuntimeError(stdout)

            # Debugging: show the output of the scp command
            log.debug("Copy stdout: " + str(stdout).replace("\n", " "))

    # -----------------------------------------------------------------

    def read_text_file(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Expand the path to absolute form
        path = self.expand_user_path(path)

        # Load the text file into a variable
        self.execute("value='cat " + path + "'")

        # Print the variable to the console, and obtain the output
        return self.execute('echo "$($value)"')

    # -----------------------------------------------------------------

    def install(self, private=False, key_password=None):

        """
        This function ...
        :param private:
        :param key_password:
        :return:
        """

        # Navigate to the home directory
        self.execute("cd ~", output=False)

        # Create the SKIRT directory
        self.create_directory("SKIRT")

        # In the SKIRT directory, create the necessary subdirectories
        self.execute("cd SKIRT", output=False)
        self.create_directories(["git", "run", "release"])

        # Clone the SKIRT repository
        if private:
            output = self.execute("git clone git@github.ugent.be:SKIRT/SKIRT.git git", expect_eof=False)
            self.ssh.expect(['id_rsa: '])
            self.ssh.sendline(key_password)

        else: self.execute("git clone https://github.com/SKIRT/SKIRT.git git", output=False)

        # Compile the SKIRT code
        self.execute("./makeSKIRT.sh", output=False)

        # Put SKIRT in the PATH environment variable

    # -----------------------------------------------------------------

    @property
    def system_name(self):

        """
        This function ...
        :return:
        """

        return self.host.system_name

    # -----------------------------------------------------------------

    @property
    def home_directory(self):

        """
        This function ...
        :return:
        """

        # Find out the path to the user's home directory and return it
        output = self.execute("echo $HOME")
        return output[0]

    # -----------------------------------------------------------------

    def expand_user_path(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        if not path.startswith("~"): return path
        else: return os.path.join(self.home_directory, path.split("~/")[1])

    # -----------------------------------------------------------------

    def find_executable(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        # Get the output of the 'which' command
        output = self.execute("which " + name)

        # Only one line is expected
        return output[0]

    # -----------------------------------------------------------------

    @property
    def working_directory(self):

        """
        This function ...
        :return:
        """

        # Find out the path to the current working directory and return it
        output = self.execute("echo $PWD")
        return output[0]

    # -----------------------------------------------------------------

    @property
    def free_cores(self):

        """
        This function ...
        :return:
        """

        return self.cores * self.cpu_load

    # -----------------------------------------------------------------

    @property
    def free_memory(self):

        """
        This function ...
        :return:
        """

        # Use the 'free' command to get information about the virtual memory usage
        #output = self.execute("free -t | grep 'Total'")
        output = self.execute("free -t | grep buffers/cache")
        splitted = output[0].split(":")[1].split()

        # Calculate the free amount of memory in gigabytes
        free = float(splitted[1]) / 1e6

        # Return the free amount of virtual memory in gigabytes
        return free

    # -----------------------------------------------------------------

    @property
    def free_space(self):

        """
        This function ...
        :return:
        """

        # Use the 'df' command to obtain information about the free disk space
        output = self.execute("df -lh")

        total = 0.0
        used = 0.0
        free = 0.0

        for entry in output[1:]:

            if not entry.startswith("/dev/"): continue

            splitted = entry.split()

            total += float(splitted[1].split("G")[0]) if "G" in splitted[1] else float(splitted[1].split("T")[0]) * 1e3
            used += float(splitted[2].split("G")[0]) if "G" in splitted[2] else float(splitted[2].split("T")[0]) * 1e3
            free += float(splitted[3].split("G")[0]) if "G" in splitted[3] else float(splitted[3].split("T")[0]) * 1e3

        # Return the amount of free memory in gigabytes
        return free

    # -----------------------------------------------------------------

    @property
    def scheduler(self):

        """
        This property ...
        :return:
        """

        return self.host.scheduler

    # -----------------------------------------------------------------

    @property
    def use_hyperthreading(self):

        """
        This function ...
        :return:
        """

        return self.host.use_hyperthreading

    # -----------------------------------------------------------------

    @property
    def multi_node_communication(self):

        """
        This function ...
        :return:
        """

        # If the remote host uses a scheduling system, check whether multi node communication is possible based on
        # the configuration of the current cluster
        if self.scheduler: return self.host.clusters[self.host.cluster_name].multi_node_communication

        # If no scheduler is used, raise an error (this function should not get called)
        else: raise RuntimeError("This function should only be called when using a remote with a scheduling system")

    # -----------------------------------------------------------------

    @property
    def virtual_memory_per_node(self):

        """
        This function ...
        :return:
        """

        # If the remote host uses a scheduling system, the amount of virtual memory memory per node is defined
        # in the configuration (this is in GB)
        if self.scheduler: return self.host.clusters[self.host.cluster_name].memory

        # If no scheduler is used, assume the number of nodes is 1 and get the total virtual memory (total swap)
        else:

            output = self.execute("free -t | grep Swap")
            splitted = output[0].split(":")[1].split()

            # Calculate the free amount of memory in gigabytes
            total_swap = float(splitted[0]) / 1e6

            # Return the free amount of virtual memory in gigabytes
            return total_swap

    # -----------------------------------------------------------------

    @property
    def nodes(self):

        """
        This function ...
        :return:
        """

        # If the remote host uses a scheduling system, the number of nodes is defined in the host configuration
        if self.scheduler: return self.host.clusters[self.host.cluster_name].nodes

        # If no scheduling system is used, assume the system is only concised of one node
        else: return 1

    # -----------------------------------------------------------------

    @property
    def cores(self):

        """
        This function ...
        :return:
        """

        # If the remote host uses a scheduling system, the number of cores on the computing nodes is defined in the configuration
        if self.scheduler: return self.host.clusters[self.host.cluster_name].cores

        # If no scheduler is used, the computing node is the actual node we are logged in to
        else:

            # Use the 'lscpu' command to obtain the total number of CPU's (=hardware threads!)
            output = self.execute("lscpu | grep '^CPU(s)'")
            cpus = int(float(output[0].split(":")[1]))

            # Return the number of physical cores
            return cpus / self.threads_per_core

    # -----------------------------------------------------------------

    @property
    def threads_per_core(self):

        """
        This function ...
        :return:
        """

        # If the remote host uses a scheduling system, the number of threads per core is defined in the configuration
        if self.scheduler: return self.host.clusters[self.host.cluster_name].threads_per_core

        # If no scheduler is used, the computing node is the actual node we are logged in to
        else:

            # Use the 'lscpu' command to get the number of hardware threads per core
            output = self.execute("lscpu | grep '^Thread(s) per core'")
            threads_per_core = int(float(output[0].split(":")[1]))

            # Return the amount of hyperthreads or 'hardware' threads per physical core
            return threads_per_core

    # -----------------------------------------------------------------

    @property
    def cpu_load(self):

        """
        This function ...
        :return:
        """

        # Use the 'top' command to get the current CPU load
        output = self.execute("top -b -n1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")

        # Convert the output into the fraction of CPU that is used
        load = float(output[0]) / 100.0

        # Return the current CPU load
        return load

    # -----------------------------------------------------------------

    @property
    def memory_load(self):

        """
        This function ...
        :return:
        """

        # Use the 'free' command to get information about the virtual memory usage
        output = self.execute("free -t | grep 'Total'")
        splitted = output[0].split(":")[1].split()

        # Calculate the total and used amount of memory in gigabytes
        total = float(splitted[0]) / 1e6
        used = float(splitted[1]) / 1e6
        free = float(splitted[2]) / 1e6

        # Return the fraction of virtual memory that is currently in use
        return used / total

    # -----------------------------------------------------------------

    def file_or_directory(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Launch a bash command to check whether the path exists as either a file or a directory on the remote file system
        output = self.execute("if [ -f " + path + " ]; then echo file; elif [ -d " + path + " ]; then echo directory; else echo None; fi")

        # Return the result
        if output[0] == "None": return None
        else: return output[0]

    # -----------------------------------------------------------------

    def is_directory(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Launch a bash command to check whether the path exists as a directory on the remote file system
        output = self.execute("if [ -d " + path + " ]; then echo True; else echo False; fi")

        # Return the result
        return output[0] == "True"

    # -----------------------------------------------------------------

    def is_file(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Launch a bash command to check whether the path exists as a regular file on the remote file system
        output = self.execute("if [ -f " + path + " ]; then echo True; else echo False; fi")

        # Return the result
        return output[0] == "True"

    # -----------------------------------------------------------------

    @property
    def host_id(self):

        """
        This function ...
        :return:
        """

        return self.host.id

# -----------------------------------------------------------------