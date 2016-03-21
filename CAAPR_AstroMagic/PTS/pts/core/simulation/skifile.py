#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.simulation.skifile Reading and updating a SKIRT parameter file.
#
# An instance of the SkiFile class in this module allows reading from and updating an existing ski file.

# -----------------------------------------------------------------

# Import standard modules
import os.path
from datetime import datetime
from lxml import etree
from numpy import arctan

# Import the relevant PTS classes and modules
from .units import SkirtUnits
from ..basics.filter import Filter
from ..tools import archive as arch

# -----------------------------------------------------------------
#  SkiFile class
# -----------------------------------------------------------------

## An instance of the SkiFile class represents a particular existing SKIRT parameter file (\em ski file).
# There are functions to read and/or update certain information in the ski file, such as obtaining or setting
# the value of a particular parameter. The intention is to encapsulate any knowledge about the ski file format
# and structure within this class, concentrating the update pain if and when that format changes.
# Consequently the public functions in this class are quite high-level, and specific rather than generic.
#
# Updates made to a SkiFile instance do \em not affect the underlying file; use the saveto() function to save
# the updated contents of a SkiFile instance to another file (or to replace the original file if so desired).
#
# A SkiFile class instance is always constructed from an existing ski file; creating a new ski file from scratch
# is not supported. To create a new ski file, start SKIRT in interactive mode (without any arguments).
#
class SkiFile:
    # ---------- Constructing and saving -----------------------------

    ## The constructor loads the contents of the specified ski file into a new SkiFile instance.
    # The filename \em must end with ".ski" or with "_parameters.xml".
    #
    def __init__(self, filepath):
        if not filepath.lower().endswith((".ski","_parameters.xml")):
            raise ValueError("Invalid filename extension for ski file")

        # Set the path to the ski file
        self.path = os.path.expanduser(filepath)

        # load the XML tree (remove blank text to avoid confusing the pretty printer when saving)
        self.tree = etree.parse(arch.opentext(self.path), parser=etree.XMLParser(remove_blank_text=True))

        # Replace path by the full, absolute path
        self.path = os.path.abspath(self.path)

    ## This function saves the (possibly updated) contents of the SkiFile instance into the specified file.
    # The filename \em must end with ".ski". Saving to and thus replacing the ski file from which this
    # SkiFile instance was originally constructed is allowed, but often not the intention.
    def saveto(self, filepath):
        if not filepath.lower().endswith(".ski"):
            raise ValueError("Invalid filename extension for ski file")
        # update the producer and time attributes on the root element
        root = self.tree.getroot()
        root.set("producer", "Python Toolkit for SKIRT (SkiFile class)")
        root.set("time", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
        # serialize the XML tree
        outfile = open(os.path.expanduser(filepath), "wb")
        outfile.write(etree.tostring(self.tree, encoding="UTF-8", xml_declaration=True, pretty_print=True))
        outfile.close()

    ## This function saves the ski file to the original path
    def save(self): self.saveto(self.path)

    # ---------- Retrieving information -------------------------------

    ## This function returns a SkirtUnits object initialized with the SKIRT unit system ('SI', 'stellar', or
    # 'extragalactic') and the flux style ('neutral', 'wavelength' or 'frequency') specified in the ski file.
    def units(self):
        unitelements = self.tree.xpath("//units/*[1]")
        if len(unitelements) == 1:
            unitsystem = unitelements[0].tag
            fluxstyle = unitelements[0].get("fluxOutputStyle", default='neutral')
        else:
            unitsystem = 'extragalactic'
            fluxstyle = 'neutral'
        return SkirtUnits(unitsystem, fluxstyle)

    ## This function returns the number of wavelengths for oligochromatic or panchromatic simulations
    def nwavelengths(self):
        # Try to get the list of wavelengths from the ski file
        wavelengths = self.wavelengths()
        # If the list is not empty, retun its size
        if wavelengths: return len(wavelengths)
        # If the list is empty, the ski file either represents a panchromatic simulation (and we can get the
        # number of points directly from the tree) or a FileWavelengthGrid is used (in which case we raise an error)
        entry = self.tree.xpath("//wavelengthGrid/*[1]")[0]
        if entry.tag == 'FileWavelengthGrid':
            raise ValueError("The number of wavelengths is not defined within the ski file. Call wavelengthsfile().")
        else:
            return int(entry.get("points"))

    ## This function returns the name of the wavelengths file that is used for the simulation, if any
    def wavelengthsfile(self):
        entry = self.tree.xpath("//FileWavelengthGrid")
        if entry: return entry[0].get("filename")
        else: return None

    ## This function returns the number of photon packages per wavelength
    def packages(self):
        # Get the MonteCarloSimulation element
        elems = self.tree.xpath("//OligoMonteCarloSimulation | //PanMonteCarloSimulation")
        if len(elems) != 1: raise ValueError("No MonteCarloSimulation in ski file")
        # Get the number of packages
        return int(float(elems[0].get("packages")))

    ## This function returns the number of dust cells
    def ncells(self):

        xpoints = self.nxcells()
        ypoints = 1
        zpoints = 1

        try:
            ypoints = self.nycells()
        except ValueError: pass

        try:
            zpoints = self.nzcells()
        except ValueError: pass

        # Return the total number of dust cells
        return xpoints*ypoints*zpoints

    ## This function returns the number of dust cells in the x direction
    def nxcells(self):
        try:
            xpoints = int(self.tree.xpath("//meshX/*")[0].get("numBins"))
        except TypeError:
            raise ValueError("The number of dust cels is not defined within the ski file")
        return xpoints

    ## This function returns the number of dust cells in the y direction
    def nycells(self):
        try:
            ypoints = int(self.tree.xpath("//meshY/*")[0].get("numBins"))
        except TypeError:
            raise ValueError("The dimension of the dust grid is lower than 2")
        return ypoints

    ## This function returns the number of dust cells in the z direction
    def nzcells(self):
        try:
            zpoints = int(self.tree.xpath("//meshZ/*")[0].get("numBins"))
        except TypeError:
            raise ValueError("The dimension of the dust grid is lower than 3")
        return zpoints

    ## This function returns the dimension of the dust grid
    def dimension(self):
        # Try to find the number of points in the y direction
        try:
            int(self.tree.xpath("//dustGridStructure/*[1]")[0].get("pointsY"))
        except TypeError:
            return 1

        # Try to find the number of points in the z direction
        try:
            int(self.tree.xpath("//dustGridStructure/*[1]")[0].get("pointsZ"))
        except TypeError:
            return 2

        # If finding the number of ypoints and zpoints succeeded, the grid is 3-dimensional
        return 3

    ## This function returns the number of dust components
    def ncomponents(self):
        components = self.tree.xpath("//CompDustDistribution/components/*")
        return int(len(components))

    ## This function returns the number of dust library items
    def nlibitems(self):
        dustlib = self.tree.xpath("//dustLib/*")[0]
        if dustlib.tag == "AllCellsDustLib":
            return self.ncells()
        elif dustlib.tag == "Dim2DustLib":
            return dustlib.attrib["pointsTemperature"] * dustlib.attrib["pointsWavelength"]
        elif dustlib.tag == "Dim1DustLib":
            return dustlib.attrib["entries"]

    ## This function returns the number of dust populations (from all dust mixes combined)
    def npopulations(self):
        npops = 0
        # For each dust mix
        for dustmix in self.tree.xpath("//mix/*[1]"):
            if dustmix.tag in ["InterstellarDustMix", "Benchmark1DDustMix", "Benchmark2DDustMix", "DraineLiDustMix"]:
                npops += 1
            elif dustmix.tag == "TrustDustMix":
                npops += int(dustmix.attrib["graphitePops"])
                npops += int(dustmix.attrib["silicatePops"])
                npops += int(dustmix.attrib["PAHPops"])
            elif dustmix.tag == "ConfigurableDustMix":
                npops += len(self.tree.xpath("//ConfigurableDustMix/populations/*"))
        return npops

    ## This function returns the number of simple instruments
    def nsimpleinstruments(self):
        return len(self.tree.xpath("//SimpleInstrument"))

    ## This function returns the number of full instruments
    def nfullinstruments(self):
        return len(self.tree.xpath("//FullInstrument"))

    ## This function returns whether transient heating is enabled
    def transientheating(self):
        return len(self.tree.xpath("//TransientDustEmissivity"))

    ## This function returns whether dust emission is enabled
    def dustemission(self):
        return len(self.tree.xpath("//dustEmissivity"))

    @property
    def emission_boost(self):
        try:
            pandustsystem = self.tree.xpath("//PanDustSystem")[0]
            return float(pandustsystem.attrib["emissionBoost"])
        except:
            raise ValueError("Not a panchromatic simulation")

    ## This function returns whether dust selfabsorption is enabled
    def dustselfabsorption(self):
        try:
            pandustsystem = self.tree.xpath("//PanDustSystem")[0]
            return (pandustsystem.attrib["selfAbsorption"] == "true")
        except:
            return False

    def enable_selfabsorption(self):

        # Get the dust system
        dust_system = self.get_dust_system()

        # Check if the dust system is of type 'PanDustSystem'
        if dust_system.tag != "PanDustSystem": raise ValueError("Not a panchromatic simulation")

        # Enable dust self-absorption
        dust_system.set("selfAbsorption", "true")

    def disable_selfabsorption(self):

        # Get the dust system
        dust_system = self.get_dust_system()

        # Check if the dust system is of type 'PanDustSystem'
        if dust_system.tag != "PanDustSystem": raise ValueError("Not a panchromatic simulation")

        # Disable dust self-absorption
        dust_system.set("selfAbsorption", "false")

    def enable_all_writing_options(self):

        # Loop over all elements in the tree
        for element in self.tree.getiterator():

            # Check if any of the settings of this element is a writing option
            for setting_name, setting_value in element.items():

                # Skip settings that are not writing settings
                if not setting_name.startswith("write"): continue

                # Set the setting to true
                element.set(setting_name, "true")

    def disable_all_writing_options(self):

        # Loop over all elements in the tree
        for element in self.tree.getiterator():

            # Check if any of the settings of this element is a writing option
            for setting_name, setting_value in element.items():

                # Skip settings that are not writing settings
                if not setting_name.startswith("write"): continue

                # Set the setting to false
                element.set(setting_name, "false")

    ## This function returns the number of pixels for each of the instruments
    def npixels(self, nwavelengths=None):
        pixels = []
        nwavelengths = nwavelengths if nwavelengths is not None else self.nwavelengths()
        instruments = self.tree.xpath("//instruments/*")
        for instrument in instruments:
            type = instrument.tag
            name = instrument.attrib["instrumentName"]
            datacube = int(instrument.attrib["pixelsX"])*int(instrument.attrib["pixelsY"])*nwavelengths
            if type == "SimpleInstrument":
                pixels.append([name, type, datacube])
            elif type == "FullInstrument":
                scattlevels = int(instrument.attrib["scatteringLevels"])
                scattering = scattlevels + 1 if scattlevels > 0 else 0
                dustemission = 1 if self.dustemission() else 0
                npixels = datacube * (3 + scattering + dustemission)
                pixels.append([name, type, npixels])
        return pixels

    ## This function returns a list of the wavelengths specified in the ski file for an oligochromatic simulation,
    # in micron. If the ski file specifies a panchromatic simulation, the function returns an empty list.
    # The current implementation requires that the wavelengths in the ski file are specified in micron.
    def wavelengths(self):
        # get the value of the wavelengths attribute on the OligoWavelengthGrid element (as a list of query results)
        results = self.tree.xpath("//OligoWavelengthGrid/@wavelengths")
        # if not found, return an empty list
        if len(results) != 1: return []
        # split the first result in separate strings, extract the numbers using the appropriate units
        units = self.units()
        return [units.convert(s,to_unit='micron',quantity='wavelength') for s in results[0].split(",")]

    ## This function returns the first instrument's distance, in the specified units (default is 'pc').
    def instrumentdistance(self, unit='pc'):
        # get the first instrument element
        instruments = self.tree.xpath("//instruments/*[1]")
        if len(instruments) != 1: raise ValueError("No instruments in ski file")
        # get the distance including the unit string
        distance = instruments[0].get("distance")
        # convert to requested units
        return self.units().convert(distance, to_unit=unit, quantity='distance')

    ## This function returns the shape of the first instrument's frame, in pixels.
    def instrumentshape(self):
        # get the first instrument element
        instruments = self.tree.xpath("//instruments/*[1]")
        if len(instruments) != 1: raise ValueError("No instruments in ski file")
        # get its shape
        return ( int(instruments[0].get("pixelsX")), int(instruments[0].get("pixelsY")) )

    ## This function returns the angular area (in sr) of a single pixel in the first instrument's frame.
    def angularpixelarea(self):
        # get the first instrument element
        instruments = self.tree.xpath("//instruments/*[1]")
        if len(instruments) != 1: raise ValueError("No instruments in ski file")
        instrument = instruments[0]
        # get the distance in m
        d = self.units().convert(instrument.get("distance"), to_unit='m', quantity='distance')
        # get the field of view in m
        fovx = self.units().convert(instrument.get("fieldOfViewX"), to_unit='m', quantity='length')
        fovy = self.units().convert(instrument.get("fieldOfViewY"), to_unit='m', quantity='length')
        # get the number of pixels
        nx = int(instrument.get("pixelsX"))
        ny = int(instrument.get("pixelsY"))
        # calculate the angular pixel area
        sx = 2 * arctan(fovx / nx / d / 2)
        sy = 2 * arctan(fovy / ny / d / 2)
        return sx * sy

    ## This function returns a list of instrument names, in order of occurrence in the ski file.
    def instrumentnames(self):
        # get the instrument elements
        instruments = self.tree.xpath("//instruments/*")
        # return their names
        return [ instr.get("instrumentName") for instr in instruments ]

    ## This function returns true if the ski file specifies a DustLib with a StaggeredAssigner, false otherwise.
    def staggered(self):
        # get any StaggeredAssigner elements as a DustLib child
        staggered = self.tree.xpath("//dustLib/*/assigner/StaggeredAssigner")
        return len(staggered) > 0

    ## This function returns the dust fraction specified in an SPHDustDistribution,
    # or 0 if the element or the attribute are not present.
    def dustfraction(self):
        # get the value of the relevant attribute on the SPHDustDistribution element (as a list of query results)
        results = self.tree.xpath("//SPHDustDistribution/@dustFraction")
        # if not found, return zero
        if len(results) != 1: return 0
        # convert the first result
        return float(results[0])

    ## This function returns the maximum gas temperature specified in an SPHDustDistribution, in Kelvin,
    # or 0 if the element or the attribute are not present.
    def maximumtemperature(self):
        # get the value of the relevant attribute on the SPHDustDistribution element (as a list of query results)
        results = self.tree.xpath("//SPHDustDistribution/@maximumTemperature")
        # if not found, return zero
        if len(results) != 1: return 0
        # extract the number from the first result, assuming units of K
        return float(results[0].split()[0])

    # ---------- Updating information ---------------------------------

    ## This function applies an XSLT transform to the ski file if an XPath condition evaluates to true.
    # The first argument is a string specifying an XPath 1.0 expression to be evaluated in the context of the XML
    # document representing the ski file; the expression value is converted to boolean according to XPath semantics.
    # If the value is true, the XSLT 1.0 transform specified in the second argument is applied to the XML document,
    # and the result replaces the original document. The second argument is a string containing one or more
    # \<xsl:template\> elements that specify the changes to be applied to the document. The \<xsl:stylesheet\>
    # element and the identity template are automatically added and must not be contained in the argument string.
    # The function returns true if the transform was applied, and false if it was not (i.e. the document is unchanged).
    def transformif(self, condition, templates):
        needed = self.tree.xpath("boolean(" + condition + ")")
        if needed:
            prefix  = '''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
                           <xsl:template match="@*|node()">
                             <xsl:copy>
                               <xsl:apply-templates select="@*|node()"/>
                             </xsl:copy>
                           </xsl:template>'''
            postfix = '''</xsl:stylesheet>'''
            transform = etree.XSLT(etree.XML(prefix + templates + postfix))
            self.tree = transform(self.tree)
        return needed

    ## This function sets the number of photon packages on the MonteCarloSimulation element in the ski file
    # to the specified value
    def setpackages(self, number):
        # get the MonteCarloSimulation element
        elems = self.tree.xpath("//OligoMonteCarloSimulation | //PanMonteCarloSimulation")
        if len(elems) != 1: raise ValueError("No MonteCarloSimulation in ski file")
        # set the attribute value
        elems[0].set("packages", str(number))

    ## This function sets the number of wavelengths
    def setnwavelengths(self, number):
        elems = self.tree.xpath("//wavelengthGrid/*[1]")
        elems[0].set("points", str(number))

    ## This function sets the number of dust cells in the x direction
    def setxdustcells(self, number):
        self.tree.xpath("//dustGridStructure/*[1]")[0].set("pointsX", str(number))

    ## This function sets the number of dust cells in the y direction
    def setydustcells(self, number):
        try:
            self.tree.xpath("//dustGridStructure/*[1]")[0].set("pointsY", str(number))
        except TypeError:
            raise ValueError("The dimension of the dust grid is lower than 2")

    ## This function sets the number of dust cells in the z direction
    def setzdustcells(self, number):
        try:
            self.tree.xpath("//dustGridStructure/*[1]")[0].set("pointsZ", str(number))
        except TypeError:
            raise ValueError("The dimension of the dust grid is lower than 3")

    ## This function increases the number of photon packages by a certain factor
    def increasepackages(self, factor):
        # Set the increased number of packages
        self.setpackages(self.packages()*factor)

    ## This function increases the number of dust cells by a certain factor
    def increasedustcells(self, factor):
        # Get the dimension of the dust grid
        dimension = self.dimension()
        # Set the increased number of dust cells in the x direction
        self.setxdustcells(int(round(self.nxcells() * factor**(1 / float(dimension)))))
        # Set the increased number of dust cells in the y direction
        if dimension > 1: self.setydustcells(int(round(self.nycells() * factor**(1 / float(dimension)))))
        # Set the increased number of dust cells in the z direction
        if dimension > 2: self.setzdustcells(int(round(self.nzcells() * factor**(1 / float(dimension)))))

    ## This function replaces any instruments in the ski file by a new list of perspective instruments
    # corresponding to the movie frames defined in the specified list. The instruments are named "0",
    # "1", "2"... corresponding to the zero-based frame index in the list. Each frame is given as a tuple
    # containing the following information: viewport shape (in pixels), viewport size, viewport position,
    # crosshair position, upwards position, and focal length (all in world coordinates, expressed in the
    # default units for length in the target ski file).
    # The components of each item are grouped in tuples, so the structure of the complete list is:
    # [ ((Nx,Ny),(Sx,Sy),(Vx,Vy,Vz),(Cx,Cy,Cz),(Ux,Uy,Uz),Fe) , ... ]
    def setperspectiveinstruments(self, frames):
        # get the instruments element
        parents = self.tree.xpath("//instruments")
        if len(parents) == 0: raise ValueError("No 'instruments' element in ski file")
        if len(parents) > 1: raise ValueError("Multiple 'instruments' elements in ski file")
        parent = parents[0]
        # remove the old instruments
        for instrument in parent.getchildren():
            parent.remove(instrument)
        # add a new instrument for each frame
        index = 0
        for pixels,size,view,cross,up,focal in frames:
            attrs = { "instrumentName" : str(index),
                      "pixelsX" : str(pixels[0]), "pixelsY" : str(pixels[1]), "width" : str(size[0]),
                      "viewX" : str(view[0]),  "viewY" : str(view[1]), "viewZ" : str(view[2]),
                      "crossX" : str(cross[0]), "crossY" : str(cross[1]), "crossZ" : str(cross[2]),
                      "upX" : str(up[0]), "upY" : str(up[1]),  "upZ" : str(up[2]), "focal" : str(focal) }
            parent.append(parent.makeelement("PerspectiveInstrument", attrs))
            index += 1

    ## This function sets the filename attribute of the SPHStellarComp element to the specified value.
    def setstarfile(self, filename):
        # get the SPHStellarComp element
        elems = self.tree.xpath("//SPHStellarComp[./sedFamily/BruzualCharlotSEDFamily]")
        if len(elems) != 1: raise ValueError("No SPHStellarComp with BruzualCharlotSEDFamily in ski file")
        # set the attribute value
        elems[0].set("filename", filename)

    ## This function sets the filename attribute of the SPHStarburstComp element to the specified value.
    def sethiifile(self, filename):
        # get the SPHStarburstComp element
        elems = self.tree.xpath("//SPHStellarComp[./sedFamily/MappingsSEDFamily]")
        if len(elems) != 1: raise ValueError("No SPHStellarComp with MappingsSEDFamily in ski file")
        # set the attribute value
        elems[0].set("filename", filename)

    ## This function sets the filename attribute of the SPHDustDistribution element to the specified value.
    def setgasfile(self, filename):
        # get the SPHDustDistribution element
        elems = self.tree.xpath("//SPHDustDistribution")
        if len(elems) != 1: raise ValueError("No SPHDustDistribution in ski file")
        # set the attribute value
        elems[0].set("filename", filename)

    ## This function sets any extentX, extentY and extentZ attributes to the specified value (converted to a string),
    # regardless of the element in which such attributes reside.
    def setextent(self, value):
        strvalue = str(value)
        for attr in self.tree.xpath("//*/@extentX"): attr.getparent().set("extentX", strvalue)
        for attr in self.tree.xpath("//*/@extentY"): attr.getparent().set("extentY", strvalue)
        for attr in self.tree.xpath("//*/@extentZ"): attr.getparent().set("extentZ", strvalue)

    ## This function returns the stellar system
    def get_stellar_system(self):

        return self.get_unique_base_element("stellarSystem")

    ## This function returns the dust system
    def get_dust_system(self):

        return self.get_unique_base_element("dustSystem")

    ## This function returns the list of stellar components
    def get_stellar_components(self, include_comments=False):

        # Get the stellar system
        stellar_system = self.get_stellar_system()

        # Get the 'components' element
        stellar_components_parents = stellar_system.xpath("components")

        # Check if only one 'components' element is present
        if len(stellar_components_parents) == 0: raise ValueError("Stellar system is not composed of components")
        elif len(stellar_components_parents) > 1: raise ValueError("Invalid ski file: multiple 'components' objects within stellar system")
        stellar_components = stellar_components_parents[0]

        # Return the stellar components as a list
        if include_comments: return stellar_components.getchildren()
        else: return [component for component in stellar_components.getchildren() if component.tag is not etree.Comment]

    ## This function returns the list of stellar component names
    def get_stellar_component_ids(self):

        # Initialize a list to contain the component ids
        ids = []

        # Get the list of stellar components
        components = self.get_stellar_components(include_comments=True)

        # keep track of the number of actual components
        number_of_components = 0

        # Loop over the components (also includes the comments)
        i = 0
        while i < len(components):

            if components[i].tag is etree.Comment:

                ids.append(components[i].text.strip())
                i += 2 # skip the next component -> it is the component corresponding to this comment

            # No name -> add the index of this component as the ID
            else:
                ids.append(number_of_components)
                i += 1

            # Increment the number of components
            number_of_components += 1

        # Return the list of names
        return ids

    ## This function returns the dust distribution
    def get_dust_distribution(self):

        # Get the dust system
        dust_system = self.get_dust_system()

        # Return the dust distribution
        return get_unique_element(dust_system, "dustDistribution")

    ## This function returns the list of dust components
    def get_dust_components(self, include_comments=False):

        # Get the dust distribution
        dust_distribution = self.get_dust_distribution()

        # Check whether the dust distribution is a CompDustDistribution
        if not dust_distribution.tag == "CompDustDistribution": raise ValueError("Dust distribution is not composed of components")

        # Get the 'components' element
        dust_components_parents = dust_distribution.xpath("components")

        # Check if only one 'components' element is present
        if len(dust_components_parents) == 0: raise ValueError("Dust distribution is not composed of components")
        elif len(dust_components_parents) > 1: raise ValueError("Invalid ski file: multiple 'components' objects within dust distribution")
        dust_components = dust_components_parents[0]

        # Return the dust components as a list
        if include_comments: return dust_components.getchildren()
        else: return [component for component in dust_components.getchildren() if component.tag is not etree.Comment]

    ## This functions returns a list with the ids of the different dust components (the id is a name if this is defined
    #  for the component, otherwise it is the index of the component)
    def get_dust_component_ids(self):

        # Initialize a list to contain the component ids
        ids = []

        # Get the list of dust components
        components = self.get_dust_components(include_comments=True)

        # keep track of the number of actual components
        number_of_components = 0

        # Loop over the components (also includes the comments)
        i = 0
        while i < len(components):

            if components[i].tag is etree.Comment:

                ids.append(components[i].text.strip())
                i += 2 # skip the next component -> it is the component corresponding to this comment

            # No name -> add the index of this component as the ID
            else:
                ids.append(number_of_components)
                i += 1

            # Increment the number of components
            number_of_components += 1

        # Return the list of names
        return ids

    ## This function returns the stellar component that is recognized by the specified id (index or name)
    def get_stellar_component(self, component_id):

        # The component identifier is an integer number -> index of stellar components
        if isinstance(component_id, int):

            # Get all the stellar components (without comments)
            components = self.get_stellar_components()

            # Return the stellar component with the specified index
            return components[component_id]

        # The component identifier is a string -> get stellar component based on description
        elif isinstance(component_id, basestring):

            # Get the stellar components
            components = self.get_stellar_components(include_comments=True)

            # Loop over the different components
            for child in components:

                if child.tag is etree.Comment and child.text.strip() == component_id:

                    # Return the child element right after the comment element
                    return child.getnext()

            # If no match is found, give an error
            raise ValueError("No stellar component found with description '" + component_id + "'")

        # Invalid component id
        else: raise ValueError("Invalid component identifier (should be integer or string)")

    ## This function returns the dust component that is recognized by the specified id (index or name)
    def get_dust_component(self, component_id):

        # The component identifier is an integer number -> index of dust components
        if isinstance(component_id, int):

            # Get all the dust components (without comments)
            components = self.get_dust_components()

            # Return the dust component with the specified index
            return components[component_id]

        # The component identifier is a string -> get dust component based on description
        elif isinstance(component_id, basestring):

            # Get the dust components
            components = self.get_dust_components(include_comments=True)

            # Loop over the different components
            for child in components:

                if child.tag is etree.Comment and child.text.strip() == component_id:

                    # Return the child element right after the comment element
                    return child.getnext()

            # If no match is found, give an error
            raise ValueError("No dust component found with description '" + component_id + "'")

        # Invalid component id
        else: raise ValueError("Invalid component identifier (should be integer or string)")

    ## This functions returns the normalization of the stellar component with the specified id
    def get_stellar_component_normalization(self, component_id):

        # Get the stellar component
        stellar_component = self.get_stellar_component(component_id)

        # Get normalization of this component
        return get_unique_element(stellar_component, "normalization")

    ## This function returns the luminosity of the stellar component with the specified id,
    #   - if the normalization is by bolometric luminosity, returns (luminosity [as Astropy quantity], None)
    #   - if the normalization is by luminosity in a specific band, returns (luminosity [as Astropy quantity], Filter object)
    #   - if the normalization is by spectral luminosity at a specific wavelength, returns (spectral luminosity [as Astropy quantity], wavelength [as Astropy quantity])
    def get_stellar_component_luminosity(self, component_id):

        # Get the stellar component normalization of the component
        normalization = self.get_stellar_component_normalization(component_id)

        # Check the type of the normalization
        if normalization.tag == "BolLuminosityStellarCompNormalization":

            # Return the total luminosity and None for the band
            return get_quantity(normalization, "luminosity", default_unit="Lsun"), None

        elif normalization.tag == "LuminosityStellarCompNormalization":

            # Return the luminosity and the corresponding band
            return get_quantity(normalization, "luminosity", default_unit="Lsun"), Filter.from_string(normalization.get("band"))

        elif normalization.tag == "SpectralLuminosityStellarCompNormalization":

            # The (spectral) luminosity
            luminosity = get_quantity(normalization, "luminosity")

            # The wavelength
            wavelength = get_quantity(normalization, "wavelength")

            # Return the luminosity and the wavelength as quantities
            return luminosity, wavelength

    ## This function sets the luminosity of the stellar component with the specified id,
    #  - if filter_or_wavelength is None, the specified luminosity [as Astropy quantity] is interpreted as a bolometric luminosity
    #  - if filter_or_wavelength is a Filter instance, the luminosity [as Astropy quantity] is interpreted as the luminosity in the corresponding band
    #  - if filter_or_wavelength is a wavelength [as an Astropy quantity], the luminosity should be the spectral luminosity [as Astropy quantity] at that wavelength
    def set_stellar_component_luminosity(self, component_id, luminosity, filter_or_wavelength=None):

        # Get the stellar component normalization of the component
        normalization = self.get_stellar_component_normalization(component_id)

        # No filter or wavelength is defined, use BolLuminosityStellarCompNormalization
        if filter_or_wavelength is None:

            # Get element that holds the normalization class
            parent = normalization.getparent()

            # Remove the old normalization
            parent.remove(normalization)

            # Make and add the new normalization element
            attrs = {"luminosity" : str(luminosity)}
            parent.append(parent.makeelement("BolLuminosityStellarCompNormalization", attrs))

        # Filter is defined, use LuminosityStellarCompNormalization
        elif isinstance(filter_or_wavelength, Filter):

            # Get element that holds the normalization class
            parent = normalization.getparent()

            # Remove the old normalization
            parent.remove(normalization)

            # Make and add the new normalization element
            attrs = {"luminosity": str(luminosity), "band": filter_or_wavelength.skirt_description}
            parent.append(parent.makeelement("LuminosityStellarCompNormalization", attrs))

        # Wavelength is defined as an Astropy quantity, use SpectralLuminosityStellarCompNormalization
        elif filter_or_wavelength.__class__.__name__ == "Quantity":

            # Get element that holds the normalization class
            parent = normalization.getparent()

            # Remove the old normalization
            parent.remove(normalization)

            # Make and add the new normalization element
            attrs = {"luminosity": str(luminosity), "wavelength": str(filter_or_wavelength)}
            parent.append(parent.makeelement("SpectralLuminosityStellarCompNormalization", attrs))

        # Invalid filter or wavelength argument
        else: raise ValueError("Invalid filter or wavelength")

    ## This function returns the normalization of the dust component with the specified id
    def get_dust_component_normalization(self, component_id):

        # Get the dust component
        dust_component = self.get_dust_component(component_id)

        # Return the normalization
        return get_unique_element(dust_component, "normalization")

    ## This function returns the dust mix for the dust component with the specified id
    def get_dust_component_mix(self, component_id):

        # Get the dust component
        dust_component = self.get_dust_component(component_id)

        # Return the dust mix
        return get_unique_element(dust_component, "mix")

    ## This functions sets a THEMIS dust mix model for the dust component with the specified id
    def set_dust_component_themis_mix(self, component_id, hydrocarbon_pops=25, enstatite_pops=25, forsterite_pops=25, write_mix=True, write_mean_mix=True, write_size=True):

        # Get the dust mix
        mix = self.get_dust_component_mix(component_id)

        # Get the parent
        parent = mix.getparent()

        # Remove the old mix
        parent.remove(mix)

        # Make and add the new mix
        attrs = {"writeMix": str(write_mix).lower(), "writeMeanMix": str(write_mean_mix).lower(),
                 "writeSize": str(write_size).lower(), "hydrocarbonPops": str(hydrocarbon_pops),
                 "enstatitePops": str(enstatite_pops), "forsteritePops": str(forsterite_pops)}
        parent.append(parent.makeelement("ThemisDustMix", attrs))

    ## This function returns the mass of the dust component with the specified id, as an Astropy quantity
    def get_dust_component_mass(self, component_id):

        # Get the dust component normalization of the component
        normalization = self.get_dust_component_normalization(component_id)

        # Check if the normalization is of type 'DustMassDustCompNormalization'
        if not normalization.tag == "DustMassDustCompNormalization": raise ValueError("Dust component normalization is not of type 'DustMassDustCompNormalization")

        # Get the dust mass and return it as a quantity
        return get_quantity(normalization, "dustMass")

    ## This function sets the mass of the dust component with the specified id. The mass should be an Astropy quantity.
    def set_dust_component_mass(self, component_id, mass):

        # Get the dust component normalization of the component
        normalization = self.get_dust_component_normalization(component_id)

        # Check if the normalization is of type 'DustMassDustCompNormalization'
        if not normalization.tag == "DustMassDustCompNormalization": raise ValueError("Dust component normalization is not of type 'DustMassDustCompNormalization")

        # Set the new dust mass
        normalization.set("dustMass", str(mass.to("Msun")) + " Msun")

    ## This function returns the wavelength grid
    def get_wavelength_grid(self):

        # Get the wavelength grid
        return self.get_unique_base_element("wavelengthGrid")

    ## This function sets the wavelength grid to a file
    def set_file_wavelength_grid(self, filename):

        # Get the wavelength grid
        wavelength_grid = self.get_wavelength_grid()

        # Get the parent
        parent = wavelength_grid.getparent()

        # Remove the old wavelength grid
        parent.remove(wavelength_grid)

        # Make and add the new wavelength grid
        attrs = {"filename": filename}
        parent.append(parent.makeelement("FileWavelengthGrid", attrs))

    ## This function returns the geometry of the stellar component with the specified id
    def get_stellar_component_geometry(self, component_id):

        # Get the stellar component
        stellar_component = self.get_stellar_component(component_id)

        # Return the geometry element of the stellar component
        return get_unique_element(stellar_component, "geometry")

    ## This function sets the geometry of the specified stellar component to a FITS file
    def set_stellar_component_fits_geometry(self, component_id, filename, pixelscale, position_angle, inclination, x_size, y_size, x_center, y_center, scale_height):

        # Get the stellar component geometry
        geometry = self.get_stellar_component_geometry(component_id)

        # Get the parent
        parent = geometry.getparent()

        # Remove the old geometry
        parent.remove(geometry)

        # Create and add the new geometry
        attrs = {"filename": filename, "pixelScale": str(pixelscale), "positionAngle": str(position_angle.to("deg")) + " deg",
                 "inclination": str(inclination.to("deg")) + " deg", "xelements": str(x_size), "yelements": str(y_size),
                 "xcenter": str(x_center), "ycenter": str(y_center), "axialScale": str(scale_height)}
        parent.append(parent.makeelement("ReadFitsGeometry", attrs))

    ## This function sets the geometry of the specified stellar component to a Sersic profile with an specific y and z flattening
    def set_stellar_component_sersic_geometry(self, component_id, index, radius, y_flattening=1, z_flattening=1):

        # Get the stellar component geometry
        geometry = self.get_stellar_component_geometry(component_id)

        # Get the parent
        parent = geometry.getparent()

        # Remove the old geometry
        parent.remove(geometry)

        # Create and add the new geometry
        attrs = {"yFlattening": str(y_flattening), "zFlattening": str(z_flattening)}
        new_geometry = parent.makeelement("TriaxialGeometryDecorator", attrs)

        attrs = {"type": "Geometry"}
        geometry_of_new_geometry = new_geometry.makeelement("geometry", attrs)

        # Add sersic profile to the geometry
        attrs = {"index": str(index), "radius": str(radius)}
        geometry_of_new_geometry.append(geometry_of_new_geometry.makeelement("SersicGeometry", attrs))

        # Add the new geometry
        parent.append(geometry)

    ## This function sets the geometry of the specified stellar component to an exponential disk profile
    def set_stellar_component_expdisk_geometry(self, component_id, radial_scale, axial_scale, radial_truncation=0, axial_truncation=0, inner_radius=0):

        # Get the stellar component geometry
        geometry = self.get_stellar_component_geometry(component_id)

        # Get the parent
        parent = geometry.getparent()

        # Remove the old geometry
        parent.remove(geometry)

        # Create and add the new exponential disk geometry
        attrs = {"radialScale": str(radial_scale), "axialScale": str(axial_scale), "radialTrunc": str(radial_truncation), "axialTrunc": str(axial_truncation), "innerRadius": str(inner_radius)}
        parent.append(parent.makeelement("ExpDiskGeometry", attrs))

    ## This function returns the SED template of the specified stellar component
    def get_stellar_component_sed(self, component_id):

        # Get the stellar component
        component = self.get_stellar_component(component_id)

        # Get the SED element
        return get_unique_element(component, "sed")

    ## This function sets the SED template of the specified stellar component to a certain model with a specific age
    #  and metallicity (but not MAPPINGS SED)
    def set_stellar_component_sed(self, component_id, template, age, metallicity):

        # The name of the template class in SKIRT
        template_class = template + "SED"

        # Get the stellar component SED
        sed = self.get_stellar_component_sed(component_id)

        # Get the parent
        parent = sed.getparent()

        # Remove the old SED element
        parent.remove(sed)

        # Create and add the new geometry
        attrs = {"age": str(age), "metallicity": str(metallicity)}
        parent.append(parent.makeelement(template_class, attrs))

    ## This function sets a MAPPINGS SED template for the stellar component with the specified id
    def set_stellar_component_mappingssed(self, component_id, metallicity, compactness, pressure, covering_factor):

        # Get the stellar component SED
        sed = self.get_stellar_component_sed(component_id)

        # Get the parent
        parent = sed.getparent()

        # Remove the old SED element
        parent.remove(sed)

        # Create and add the new geometry
        attrs = {"metallicity": str(metallicity), "compactness": str(compactness), "pressure": str(pressure), "coveringFactor": str(covering_factor)}
        parent.append(parent.makeelement("MappingsSED", attrs))

    ## This function returns the dust emissivity
    def get_dust_emissivity(self):

        # Get the dust system
        dust_system = self.get_dust_system()

        # Return the dust emissivity element
        return get_unique_element(dust_system, "dustEmissivity")

    ## This function sets a transient dust emissivity for the simulation
    def set_transient_dust_emissivity(self):

        # Get the dust emissivity
        emissivity = self.get_dust_emissivity()

        # Get the parent
        parent = emissivity.getparent()

        # Remove the old emissivity
        parent.remove(emissivity)

        # Create and add the new emissivity
        parent.append(parent.makeelement("TransientDustEmissivity", {}))

    ## This function returns the dust library
    def get_dust_lib(self):

        # Get the dust system
        dust_system = self.get_dust_system()

        # Return the dust lib element
        return get_unique_element(dust_system, "dustLib")

    ## This function sets the dust library to an AllCellsDustLib
    def set_allcells_dust_lib(self):

        # Get the dust lib
        lib = self.get_dust_lib()

        # Get the parent
        parent = lib.getparent()

        # Remove the old DustLib element
        parent.remove(lib)

        # Create and add the new library
        parent.append(parent.makeelement("AllCellsDustLib", {}))

    ## This function sets the dust library to a 2D dust library
    def set_2d_dust_lib(self, temperature_points=25, wavelength_points=10):

        # Get the dust lib
        lib = self.get_dust_lib()

        # Get the parent
        parent = lib.getparent()

        # Remove the old DustLib element
        parent.remove(lib)

        # Create and add the new library
        attrs = {"pointsTemperature": str(temperature_points), "pointsWavelength": str(wavelength_points)}
        parent.append(parent.makeelement("Dim2DustLib", attrs))

    ## This function sets the dust library to a 1D dust library
    def set_1d_dust_lib(self, points):

        # Get the dust lib
        lib = self.get_dust_lib()

        # Get the parent
        parent = lib.getparent()

        # Remove the old DustLib element
        parent.remove(lib)

        # Create and add the new library
        attrs = {"entries": str(points)}
        parent.append(parent.makeelement("Dim1DustLib", attrs))

    ## This function returns the dust grid
    def get_dust_grid(self):

        # Get the dust system
        dust_system = self.get_dust_system()

        # Return the dust grid
        return get_unique_element(dust_system, "dustGrid")

    ## This function sets a binary tree dust grid for the dust system
    def set_binary_tree_dust_grid(self, min_x, max_x, min_y, max_y, min_z, max_z, write_grid=True, min_level=15,
                                  max_level=25, search_method="Neighbor", sample_count=100, max_optical_depth=0,
                                  max_mass_fraction=1e-6, max_dens_disp_fraction=0, direction_method="Alternating",
                                  assigner="IdenticalAssigner"):

        # Get the dust grid
        grid = self.get_dust_grid()

        # Get the parent
        parent = grid.getparent()

        # Remove the old grid element
        parent.remove(grid)

        # Create and add the new grid
        attrs = {"minX": str(min_x), "maxX": str(max_x), "minY": str(min_y), "maxY": str(max_y), "minZ": str(min_z),
                 "maxZ": str(max_z), "writeGrid": str(write_grid).lower(), "minLevel": str(min_level),
                 "maxLevel": str(max_level), "searchMethod": search_method, "sampleCount": str(sample_count),
                 "maxOpticalDepth": str(max_optical_depth), "maxMassFraction": str(max_mass_fraction),
                 "maxDensDispFraction": str(max_dens_disp_fraction), "directionMethod": direction_method,
                 "assigner": assigner}
        parent.append(parent.makeelement("BinTreeDustGrid", attrs))

    ## This function sets an octtree dust grid for the dust system
    def set_octtree_dust_grid(self, min_x, max_x, min_y, max_y, min_z, max_z, write_grid=True, min_level=2,
                              max_level=6, search_method="Neighbor", sample_count=100, max_optical_depth=0,
                              max_mass_fraction=1e-6, max_dens_disp_fraction=0, barycentric=False,
                              assigner="IdenticalAssigner"):

        # Get the dust grid
        grid = self.get_dust_grid()

        # Get the parent
        parent = grid.getparent()

        # Remove the old grid element
        parent.remove(grid)

        # Create and add the new grid
        attrs = {"minX": str(min_x), "maxX": str(max_x), "minY": str(min_y), "maxY": str(max_y), "minZ": str(min_z),
                 "maxZ": str(max_z), "writeGrid": str(write_grid).lower(), "minLevel": str(min_level),
                 "maxLevel": str(max_level), "searchMethod": search_method, "sampleCount": sample_count,
                 "maxOpticalDepth": str(max_optical_depth), "maxMassFraction": str(max_mass_fraction),
                 "maxDensDispFraction": str(max_dens_disp_fraction), "barycentric": str(barycentric).lower(),
                 "assigner": assigner}
        parent.append(parent.makeelement("OctTreeDustGrid", attrs))

    ## This function returns a list of the instruments in the ski file, or the 'instruments' element if as_list is False
    def get_instruments(self, as_list=True):

        # Get the instrument system
        instrument_system = self.get_unique_base_element("instrumentSystem")

        # Get the 'instruments' element
        instruments_parents = instrument_system.xpath("instruments")

        # Check if only one 'instruments' element is present
        if len(instruments_parents) == 0: raise ValueError("No instruments found")
        elif len(instruments_parents) > 1: raise ValueError("Invalid ski file: multiple 'instruments' objects within instrument system")
        instruments_element = instruments_parents[0]

        # Return the instruments as a list
        if as_list: return instruments_element.getchildren()
        else: return instruments_element

    ## This function returns the names of all the instruments in the ski file as a list
    def get_instrument_names(self):

        # Initialize a list to contain the names
        names = []

        # Get the list of instruments
        instruments = self.get_instruments()

        # Loop over the instruments
        for instrument in instruments:

            # Get the instrument name
            instrument_name = instrument.get("instrumentName")

            # Add the name to the list
            names.append(instrument_name)

        # Return the list of names
        return names

    ## This function removes the instrument with the specified name
    def remove_instrument(self, name):

        # Get the instrument with the specified name
        instrument = self.get_instrument(name)

        # Get element that holds the instrument class
        parent = instrument.getparent()

        # Remove the instrument
        parent.remove(instrument)

    ## This function removes all instruments
    def remove_all_instruments(self):

        for name in self.get_instrument_names():
            self.remove_instrument(name)

    ## This function adds a FullInstrument to the instrument system
    def add_full_instrument(self, name, distance, inclination, azimuth, position_angle, field_x, field_y,
                            pixels_x, pixels_y, center_x, center_y, scattering_levels=0):

        # Get the 'instruments' element
        instruments = self.get_instruments(as_list=False)

        # Make and add the new FullInstrument
        attrs = {"instrumentName": name, "distance": str(distance), "inclination": str(inclination),
                 "azimuth": str(azimuth), "positionAngle": str(position_angle), "fieldOfViewX": str(field_x),
                 "fieldOfViewY": str(field_y), "pixelsX": str(pixels_x), "pixelsY": str(pixels_y),
                 "centerX": str(center_x), "centerY": str(center_y), "scatteringLevels": str(scattering_levels)}
        instruments.append(instruments.makeelement("FullInstrument", attrs))

    ## This function adds a SimpleInstrument to the instrument system
    def add_simple_instrument(self, name, distance, inclination, azimuth, position_angle, field_x, field_y,
                              pixels_x, pixels_y, center_x, center_y):

        # Get the 'instruments' element
        instruments = self.get_instruments(as_list=False)

        # Make and add the new SimpleInstrument
        attrs = {"instrumentName": name, "distance": str(distance), "inclination": str(inclination),
                 "azimuth": str(azimuth), "positionAngle": str(position_angle), "fieldOfViewX": str(field_x),
                 "fieldOfViewY": str(field_y), "pixelsX": str(pixels_x), "pixelsY": str(pixels_y),
                 "centerX": str(center_x), "centerY": str(center_y)}
        instruments.append(instruments.makeelement("SimpleInstrument", attrs))

    ## This function adds an SEDInstrument to the instrument system
    def add_sed_instrument(self, name, distance, inclination, azimuth, position_angle):

        # Get the 'instruments' element
        instruments = self.get_instruments(as_list=False)

        # Make and add the new SEDInstrument
        attrs = {"instrumentName": name, "distance": str(distance), "inclination": str(inclination),
                 "azimuth": str(azimuth), "positionAngle": str(position_angle)}
        instruments.append(instruments.makeelement("SEDInstrument", attrs))

    ## This function returns the instrument with the specified name
    def get_instrument(self, name):

        # Get the list of instruments
        instruments = self.get_instruments()

        # Loop over the instruments
        for instrument in instruments:

            # Get the instrument name
            instrument_name = instrument.get("instrumentName")

            # If the name matches, return
            if name == instrument_name: return instrument

        raise ValueError("No instrument with the name '" + name + "'")

    ## This function changes the name of the specified instrument
    def set_instrument_name(self, old_name, new_name):

        # Get the instrument with the specified name
        instrument = self.get_instrument(old_name)

        # Set the new name
        instrument.set("instrumentName", new_name)

    ## This function returns the distance of the specified instrument as an Astropy quantity
    def get_instrument_distance(self, name):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Return the distance
        return get_quantity(instrument, "distance")

    ## This function sets the distance of the specified instruments. The distance should be an Astropy quantity.
    def set_instrument_distance(self, name, value):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Set the distance
        set_quantity(instrument, "distance", value)

    ## This function returns the inclination of the specified instrument as an Astropy Angle.
    def get_instrument_inclination(self, name):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Return the inclination
        return get_quantity(instrument, "inclination")

    ## This function sets the inclination of the specified instrument. The inclination should be an Astropy Angle or quantity.
    def set_instrument_inclination(self, name, value):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Set the inclination
        set_quantity(instrument, "inclination", value)

    ## This function returns the azimuth angle of the specified instrument as an Astropy Angle.
    def get_instrument_azimuth(self, name):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Return the azimuth
        return get_quantity(instrument, "azimuth")

    ## This function sets the azimuth angle of the specified instrument. The angle should be an Astropy Angle or quantity.
    def set_instrument_azimuth(self, name, value):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Set the azimuth angle
        set_quantity(instrument, "azimuth", value)

    ## This function returns the position angle of the specified instrument as an Astropy Angle.
    def get_instrument_pa(self, name):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Return the position angle
        return get_quantity(instrument, "positionAngle")

    ## This function sets the position angle of the specified instrument. The angle should be an Astropy Angle or quantity.
    def set_instrument_pa(self, name, value):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Set the position angle
        set_quantity(instrument, "positionAngle", value)

    ## This function sets the orientation of the specified instrument. The angles should be Astropy Angle or Quantity instances.
    def set_instrument_orientation(self, name, inclination, position_angle, azimuth):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Set the inclination
        set_quantity(instrument, "inclination", inclination)
        set_quantity(instrument, "positionAngle", position_angle)
        set_quantity(instrument, "azimuth", azimuth)

    ## This function sets the orientation of the specified instrument to a face-on orientation.
    def set_instrument_orientation_faceon(self, name):

        from astropy.coordinates import Angle

        # XY plane
        inclination = Angle(0., "deg")
        position_angle = Angle(90., "deg")
        azimuth = Angle(0.0, "deg")

        # Set the angles
        self.set_instrument_orientation(name, inclination, position_angle, azimuth)

    ## This function sets the orientation of the specified instrument to an edge-on orientation
    def set_instrument_orientation_edgeon(self, name):

        from astropy.coordinates import Angle

        # XZ plane
        inclination = Angle(90., "deg")
        position_angle = Angle(0., "deg")
        azimuth = Angle(-90., "deg")

        # Set the angles
        self.set_instrument_orientation(name, inclination, position_angle, azimuth)

    ## This function returns the size of the specified instrument as a tuple (size_x, size_y)
    def get_instrument_size(self, name):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Return the size
        return int(instrument.get("pixelsX")), int(instrument.get("pixelsY"))

    ## This function sets the size of the specified instrument
    def set_instrument_size(self, name, x_size, y_size):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Set the size
        instrument.set("pixelsX", str(x_size))
        instrument.set("pixelsY", str(y_size))

    ## This function returns the field of view of the specified instrument as a tuple (field_x, field_y)
    def get_instrument_field(self, name):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Get the field of view
        return get_quantity(instrument, "fieldOfViewX"), get_quantity(instrument, "fieldOfViewY")

    ## This function sets the field of view of the specified instrument
    def set_instrument_field(self, name, x_field, y_field):

        # Get the instrument with this name
        instrument = self.get_instrument(name)

        # Set the field of view
        set_quantity(instrument, "fieldOfViewX", x_field)
        set_quantity(instrument, "fieldOfViewY", y_field)

    ## This (experimental) function converts the ski file structure into a (nested) python dictionary
    def to_dict(self):

        return recursive_dict(self.tree.getroot())

    ## This (experimental) function converts the ski file structure into json format
    def to_json(self):

        """
        This function returns the ski file to a json format
        :return:
        """

        import json
        return json.dumps(self.to_dict())

    ## This function returns the xml tree element with the specified name that is at the base level of the simulation hierarchy
    def get_unique_base_element(self, name):

        return get_unique_element(self.tree.getroot(), "//"+name)

# -----------------------------------------------------------------

## This function returns the xml tree element with the specified name that is a child of the specified element
def get_unique_element(element, name):

    # Get child element of the given element
    parents = element.xpath(name)

    # Check if only one child element is present
    if len(parents) == 0: raise ValueError("Invalid ski file: no '" + name + "' elements within '" + element.tag + "'")
    elif len(parents) > 1: raise ValueError("Invalid ski file: multiple '" + name + "' elements within '" + element.tag + "'")
    parents = parents[0]

    # Check if only one child object is present
    if len(parents) == 0: raise ValueError("Invalid ski file: no '" + name + "' elements within '" + element.tag + "'")
    elif len(parents) > 1: raise ValueError("Invalid ski file: multiple '" + name + "' elements within '" + element.tag + "'")
    child = parents[0]

    # Return the child element
    return child

# -----------------------------------------------------------------

## This function returns the value of a certain parameter of the specified tree element as an Astropy quantity. The
#  default unit can be specified which is used when the unit is not described in the ski file.
def get_quantity(element, name, default_unit=None):

    # Import Astropy here to avoid import errors for this module for users without an Astropy installation
    from astropy.units import Unit

    splitted = element.get(name).split()
    value = float(splitted[0])
    try: unit = splitted[1]
    except IndexError: unit = default_unit

    # Create a quantity object
    if unit is not None: value = value * Unit(unit)
    return value

# -----------------------------------------------------------------

## This function sets the value of a certain parameter of the specified tree element from an Astropy quantity.
def set_quantity(element, name, value, default_unit=None):

    # Import Astropy here to avoid import errors for this module for users without an Astropy installation
    from astropy.units import Unit

    try:

        # If this works, assume it is a Quantity (or Angle)
        unit = value.unit

        # Works for Angles as well (str(angle) gives something that is not 'value + unit'
        to_string = str(value.to(value.unit).value) + " " + str(unit)

    except AttributeError:

        if default_unit is not None: to_string = str(value) + " " + str(Unit(default_unit))
        else: to_string = str(value)  # dimensionless quantity

    # Set the value in the tree element
    element.set(name, to_string)

# -----------------------------------------------------------------

def recursive_dict(element):
    return element.tag, dict(map(recursive_dict, element)) or element.text

# -----------------------------------------------------------------
