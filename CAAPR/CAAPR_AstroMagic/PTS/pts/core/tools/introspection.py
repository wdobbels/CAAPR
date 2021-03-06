#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.introspection Contains some useful variables that store SKIRT and PTS installation directories
#  and provides functions for checking the presence and use of SKIRT and PTS dependencies.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import sys
import imp
import inspect
import socket
import subprocess
import numpy as np
from operator import itemgetter, methodcaller
from collections import defaultdict
from contextlib import contextmanager
from distutils.spawn import find_executable
from importlib import import_module
import pip
import pkg_resources

# Import the relevant PTS classes and modules
from . import filesystem as fs

# -----------------------------------------------------------------

subprojects = ["core", "magic", "eagle", "modeling", "dustpedia"]

# The path to the root PTS directory
pts_root_dir = inspect.getfile(inspect.currentframe()).split("/pts")[0]

# The path to the PTS package directory (PTS/pts)
pts_package_dir = os.path.join(pts_root_dir, "pts")

# The path to the PTS user directory (PTS/user)
pts_user_dir = os.path.join(pts_root_dir, "user")

# The path to the PTS user/hosts directory
pts_user_hosts_dir = os.path.join(pts_user_dir, "hosts")

# The path to the PTS user/accounts directory
pts_user_accounts_dir = os.path.join(pts_user_dir, "accounts")

# The path to the PTS do directory containing launchable scripts (PTS/pts/do)
pts_do_dir = os.path.join(pts_package_dir, "do")

# The path to the main directory for a given PTS subproject
def pts_subproject_dir(subproject): return os.path.join(pts_package_dir, subproject)

# The path to the 'config' directory for a given PTS subproject
def pts_config_dir(subproject): return os.path.join(pts_package_dir, subproject, "config")

# The path to the 'dat' directory for a given PTS subproject
def pts_dat_dir(subproject): return os.path.join(pts_package_dir, subproject, "dat")

# -----------------------------------------------------------------

def pts_version():
    label = subprocess.check_output(["git", "describe", "--tags"])
    return label[:-1]

# -----------------------------------------------------------------

# The path to the SKIRT executable
skirt_path = find_executable("skirt")

# The path to the root SKIRT directory
skirt_root_dir = skirt_path.split("/release")[0] if skirt_path is not None else None

# The path to the SKIRT repository
skirt_repo_dir = os.path.join(skirt_root_dir, "git") if skirt_path is not None else None

# The path to the SKIRT release directory
skirt_release_dir = os.path.join(skirt_root_dir, "release") if skirt_path is not None else None

# The path to the SKIRT run directory
skirt_run_dir = os.path.join(skirt_root_dir, "run") if skirt_path is not None else None

# -----------------------------------------------------------------

def host_name():

    """
    This function ...
    :return:
    """

    return socket.gethostname()

# -----------------------------------------------------------------

def skirt_is_present():

    """
    This function ...
    :return:
    """

    return skirt_path is not None

# -----------------------------------------------------------------

def qmake_path():

    """
    This function ...
    :return:
    """

    try: output = subprocess.check_output(["which", "qmake"]).split("\n")[0]
    except subprocess.CalledProcessError: return None

    return output

# -----------------------------------------------------------------

def qmake_is_present():

    """
    This function ...
    :return:
    """

    return qmake_path() is not None

# -----------------------------------------------------------------

def pts_installation_is_conform():

    """
    This function ...
    :return:
    """

    pts_root_dir_name = fs.name(pts_root_dir)
    return pts_root_dir_name == "PTS"

# -----------------------------------------------------------------

def skirt_installation_is_conform():

    """
    This function ...
    """

    skirt_root_dir_name = fs.name(skirt_root_dir)
    return skirt_root_dir_name == "SKIRT"

# -----------------------------------------------------------------

def remote_host_ids():

    """
    This function ...
    :return:
    """

    # Search for files that define remote host configurations
    hosts_directory = os.path.join(pts_user_dir, "hosts")
    if not os.path.isdir(hosts_directory): os.makedirs(hosts_directory)

    # Initialize a list to contain the host ids
    ids = []

    # Loop over the configuration files in the hosts directory
    for name in fs.files_in_path(hosts_directory, extension="cfg", returns="name"):

        # Skip the template configuration file
        if name == "template": continue

        # Add the host name to the list of host ids
        ids.append(name)

    # Return the list of host ids
    return ids

# -----------------------------------------------------------------

def simulations_files_for_host(host_id):

    """
    This function checks whether there are simulation files corresponding to this host ID
    :param host_id:
    :return:
    """

    # Determine the path to the SKIRT run subdirectory for the specified host
    host_run_dir = os.path.join(skirt_run_dir, host_id)

    # Return the list of simulation file paths corresponding to the specified host
    return fs.files_in_path(host_run_dir, extension="sim")

# -----------------------------------------------------------------

def has_mpi():

    """
    This function ...
    :return:
    """

    # Try opening the 'mpirun' executable
    try:
        devnull = open(os.devnull)
        subprocess.Popen("mpirun", stdout=devnull, stderr=devnull).communicate()
        return True
    except: return False

# -----------------------------------------------------------------

def mpi_version():

    """
    This function ...
    :return:
    """

    # Execute 'mpirun --version' and get the output
    process = subprocess.Popen(["mpirun", "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = process.communicate()[0]

    # Return the relevant portion of the output
    return "OpenMPI " + output.splitlines()[0].split(") ")[1]

# -----------------------------------------------------------------

def skirt_version():

    """
    This function ...
    :return:
    """

    # Execute skirt with incorrect argument list and get its output
    process = subprocess.Popen([skirt_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = process.communicate()[0]

    # Return the relevant portion of the output
    return "SKIRT" + output.splitlines()[0].partition("SKIRT")[2]

# -----------------------------------------------------------------

def get_pip_versions():

    """
    This function ...
    :return:
    """

    packages = dict()

    # Launch the 'pip freeze' command and get the output
    output = subprocess.check_output(["pip", "list"])

    # Loop over the different package names and record the version number
    for entry in output.split("\n"):

        # Skip empty strings
        if not entry: continue

        # Get the package name and version
        name, version = entry.split(" (")
        version = version.split(")")[0]

        # Add them to the dictionary
        packages[name.lower()] = version

    # Return the dictionary
    return packages

# -----------------------------------------------------------------

@contextmanager
def ignore_site_packages_paths():

    """
    This function ...
    :return:
    """

    paths = sys.path[:]
    # remove working directory so that all
    # local imports fail
    if os.getcwd() in sys.path:
        sys.path.remove(os.getcwd())
    # remove all third-party paths
    # so that only stdlib imports will succeed
    sys.path = list(set(filter(
        None,
        filter(lambda i: all(('site-packages' not in i,
                              'python' in i or 'pypy' in i)),
               map(methodcaller('lower'), sys.path))
    )))
    yield
    sys.path = paths

# -----------------------------------------------------------------

def is_std_lib(module):

    """
    This function ...
    :param module:
    :return:
    """

    if not module:
        return False

    if module in sys.builtin_module_names:
        return True

    with ignore_site_packages_paths():
        imported_module = sys.modules.pop(module, None)
        try:
            import_module(module)
        except ImportError:
            return False
        else:
            return True
        finally:
            if imported_module:
                sys.modules[module] = imported_module

# -----------------------------------------------------------------

def get_all_dependencies():

    """
    This function ...
    :return:
    """

    # Create an empty dictionary to contain the required modules together with the places of use
    modules = defaultdict(set)

    # Recursively loop over all files inside this working directory
    for directory, subdirs, files in os.walk(pts_package_dir):

        python_files = [filename for filename in files if filename.endswith(".py")]

        # Loop over all files in the (sub)directory
        for filename in python_files:

            # Determine the full path to this file
            filepath = os.path.join(directory, filename)

            has_absolute_import = False
            modules_file = []

            # Read the lines of the script file
            for line in open(filepath, 'r'):

                # Look for an 'import yyy' or 'from yyy import zzz' statement
                if line.startswith("import ") or (line.startswith("from ") and "import" in line):

                    # Set absolute import
                    if "absolute_import" in line: has_absolute_import = True

                    # Get the name of the module
                    module = line.split()[1].split(".")[0]

                    # Skip "pts"
                    if module == "pts": continue

                    # Add the module name to the list
                    if module: modules_file.append(module)

            # If absolute import is used, add all the imported modules (they must be external packages)
            if has_absolute_import:

                # Loop over found imported modules for this file
                for module_name in modules_file: modules[module_name].add(filepath)

            # If absolute import is not used, check whether some of the module names are just local (in the same directory)
            else:

                local_module_names_in_dir = [filename[:-3] for filename in python_files if "__init__" not in filename]

                for module_name in modules_file:

                    if module_name in local_module_names_in_dir: continue

                    if module_name == "constants" or module_name == "genome": print(module_name, filepath, local_module_names_in_dir)

                    modules[module_name].add(filepath)

    return modules

# -----------------------------------------------------------------

def add_dependencies(dependencies, script_path, encountered_internal_modules, prefix="", debug=False):

    """
    This function ...
    :param dependencies:
    :param script_path:
    :param encountered_internal_modules:
    :param prefix:
    :return:
    """

    # Skip files that are not python scripts
    if not script_path.endswith(".py"): raise ValueError("Not a valid script path")

    # Read the lines of the script file
    import_lines = []
    for line in open(script_path, 'r'):

        # If the current line does not contain an 'import yyy' or 'from yyy import zzz' statement, skip it
        if not (line.startswith("import ") or (line.startswith("from ") and "import" in line)): continue

        import_lines.append(line)

    if debug:
        print("Import statements found in " + script_path + ":")
        for import_line in import_lines:
            print(" - " + import_line[:-1])

    # Loop over the lines where something is imported
    for line in import_lines:

        # Get the path to the modules that are being imported in the current line
        modules = get_modules(line, script_path, debug=debug)

        for module in modules:

            # Check if the imported module refers to a PTS module or an external package
            if module.startswith("/"): # a PTS module

                if module in encountered_internal_modules: continue
                else:
                    encountered_internal_modules.add(module)
                    add_dependencies(dependencies, module, encountered_internal_modules, prefix=prefix+"  ", debug=debug)

            else: dependencies[module].add(script_path)

# -----------------------------------------------------------------

def installed_python_packages():

    """
    This function ...
    :return:
    """

    # Initialize dictionary to contain the package names and version numbers
    packages = dict()

    # Get all python distributions
    distributions = pip.get_installed_distributions()

    # Loop over the distributions
    for distribution in distributions:

        # Get name and version
        top_level_meta_data = list(distribution._get_metadata('top_level.txt'))
        import_name = top_level_meta_data[0] if len(top_level_meta_data) > 0 else distribution.project_name
        version = str(distribution.parsed_version)

        # possible other interesting properties of an entry in the distributions list:
        # .egg_name()
        # .as_requirement()
        # .parsed_version
        # .has_version()
        # .project_name
        # .py_version
        # .requires()

        # Add entry to the dictionary
        packages[import_name] = version

    # Return the dictionary
    return packages

# -----------------------------------------------------------------

def is_present_package(package):

    """
    This function ...
    :return:
    """

    try:
        imp.find_module(package)
        return True
    except ImportError: return False

# -----------------------------------------------------------------

def get_modules(import_statement, script_path, debug=False):

    """
    This function ...
    :param import_statement:
    :param script_path:
    :param debug:
    :return:
    """

    splitted = import_statement.split()

    if len(splitted) <= 2: imported = []

    elif "," in splitted[3]:

        imported = [splitted[3][:-1]]

        for more in splitted[4:]:

            if "," in more: more = more[:-1]
            imported.append(more)

    else: imported = [splitted[3]]

    which = []

    # Check if this line denotes a relative import statement
    if splitted[1].startswith("."):

        after_dots = splitted[1].lstrip(".")

        number_of_dots = len(splitted[1]) - len(after_dots)

        # Determine the path to the PTS subpackage
        subpackage_dir = script_path
        for i in range(number_of_dots):
            subpackage_dir = os.path.dirname(subpackage_dir)

        subpackage_name = after_dots.split(".")[0]

        #subpackage_path = os.path.join(subpackage_dir, subpackage_name) # I had this before, how could this be working??

        subpackage_path = fs.join(subpackage_dir, after_dots.replace(".", "/"))

        for name in imported: which.append(which_module(subpackage_path, name))

    # Absolute import of a pts class or module
    elif splitted[1].startswith("pts"):

        parts = splitted[1].split(".")[1:]

        subpackage_dir = pts_package_dir
        for part in parts:
            subpackage_dir = os.path.join(subpackage_dir, part)

        for name in imported: which.append(which_module(subpackage_dir, name))

    # External module
    else:

        # Get the name of the module
        module = splitted[1].split(".")[0]

        which.append(module)

    return which

# -----------------------------------------------------------------

def which_module(subpackage, name):

    """
    This function ...
    :param subpackage:
    :param name:
    :return:
    """

    if "," in name: print(name)
    if name.islower() and os.path.isfile(os.path.join(subpackage, name + ".py")): return os.path.join(subpackage, name + ".py")

    elif os.path.isfile(subpackage + ".py"):

        #print("  " + subpackage + ".py")
        return subpackage + ".py"

    elif os.path.isfile(os.path.join(subpackage, "__init__.py")):

        #print("  " + subpackage + ":")
        return os.path.join(subpackage, "__init__.py")

    else: raise ValueError("Don't know how to get further with " + subpackage + " and " + name)

# -----------------------------------------------------------------

def get_scripts():

    """
    This function ...
    :return:
    """

    # Loop over the directories within the 'do' subpackage
    scripts = []
    for item in os.listdir(pts_do_dir):

        # Get the full path to the item
        item_path = os.path.join(pts_do_dir, item)

        # Skip items that are not directories
        if not os.path.isdir(item_path): continue

        # Loop over the files in the directory
        for name in os.listdir(item_path):

            # Get the full name to the file
            file_path = os.path.join(item_path, name)

            # Skip items that are not files
            if not os.path.isfile(file_path): continue

            # Add the file path
            if file_path.endswith(".py") and "__init__" not in file_path: scripts.append((item, name))

    # Return the sorted list of script names
    return sorted(scripts, key=itemgetter(1))

# -----------------------------------------------------------------

def find_matches_scripts(name, scripts):

    """
    This function ...
    :param name:
    :param scripts:
    :return:
    """

    # Get a list of the script names that match the first command line argument, if there is one
    if "/" in name:

        matches = []
        dir_name = name.split("/")[0]
        script_name = name.split("/")[1]

        # Loop over all found items
        for item in scripts:
            if item[0] == dir_name and item[1].startswith(script_name): matches.append(item)

        return matches

    # Return the list of matching scripts
    elif name is not None: return filter(lambda item: item[1].startswith(name), scripts)
    else: return []

# -----------------------------------------------------------------

def find_matches_tables(name, tables):

    """
    This function ...
    :param name:
    :param tables:
    :return:
    """

    # ...
    if "/" in name:

        matches = []
        dir_name = name.split("/")[0]
        script_name = name.split("/")[1]

        for subproject in tables:

            if dir_name != subproject: continue

            table = tables[subproject]

            for i in range(len(table["Command"])):

                if table["Command"][i].startswith(script_name): matches.append((subproject, i))

        return matches

    elif name is not None:

        matches = []

        for subproject in tables:

            table = tables[subproject]

            for i in range(len(table["Command"])):
                if table["Command"][i].startswith(name): matches.append((subproject, i))

        return matches

    else: return []

# -----------------------------------------------------------------

def get_arguments_tables():

    """
    This function ...
    :return:
    """

    tables = dict()

    # Loop over the subprojects
    for subproject in subprojects:

        table_path = fs.join(pts_subproject_dir(subproject), "commands.dat")
        if not fs.is_file(table_path): continue

        # Get the columns
        commands, configuration, where, description = np.genfromtxt(table_path, delimiter=" | ", dtype=str, unpack=True)

        # Table
        table = {"Command": commands, "Configuration": configuration, "Path": where, "Description": description}
        tables[subproject] = table

    # Return the tables
    return tables

# -----------------------------------------------------------------

def show_all_available(scripts, tables=None):

    """
    This function ...
    :param scripts:
    :param tables:
    :return:
    """

    print("No match found. Available commands:")

    # Combine scripts and tables
    for subproject in tables:
        table = tables[subproject]
        for i in range(len(table["Command"])):
            scripts.append((subproject, table["Command"][i] + ".py", table["Description"][i]))

    # Sort on the 'do' subfolder name
    scripts = sorted(scripts, key=itemgetter(0))

    current_dir = None
    for script in scripts:

        description = "  " + script[2] if len(script) == 3 else ""

        if current_dir == script[0]:
            print(" " * len(current_dir) + "/" + script[1][:-3] + description)
        else:
            print(script[0] + "/" + script[1][:-3] + description)
            current_dir = script[0]

# -----------------------------------------------------------------

def show_possible_matches(matches, table_matches=None, tables=None):

    """
    This function ...
    :param matches:
    :param table_matches:
    :param tables:
    :return:
    """

    print("The command you provided is ambiguous. Possible matches:")

    # Combine script and table matches
    for subproject, index in table_matches:
        command = tables[subproject]["Command"][index]
        description = tables[subproject]["Description"][index]
        matches.append((subproject, command + ".py", description))

    # Sort on the 'do' subfolder name
    matches = sorted(matches, key=itemgetter(0))

    current_dir = None
    for script in matches:

        description = "  " + script[2] if len(script) == 3 else ""

        if current_dir == script[0]:
            print(" " * len(current_dir) + "/" + script[1][:-3] + description)
        else:
            print(script[0] + "/" + script[1][:-3] + description)
            current_dir = script[0]

# -----------------------------------------------------------------
