#import ast
#import os
#import pickle
#import re
import zipfile
from argparse import Namespace
#from errno import ENOENT
#from warnings import catch_warnings, simplefilter, warn

import h5py
import numpy as np
#import astropy.io.fits as pyfits
from igor import binarywave

def start_step_n(start, step, n) :
    """
    Return an array that starts at value `start` and goes `n`
    steps of `step`.
    """
    end = start + n*step
    return np.linspace(start, end, n)

class Data_loader():
    def __init__(self,data_tab):
        self.data_tab = data_tab

    @staticmethod
    def read_metadata(keys, metadata_file):
        metadata = Namespace()
        for line in metadata_file.readlines() :
            # Split at 'equals' sign
            tokens = line.decode('utf-8').split('=')
            for key, name, dtype in keys :
                if tokens[0] == key :
                    # Split off whitespace or garbage at the end
                    value = tokens[1].split()[0]
                    # And cast to right type
                    value = dtype(value)
                    metadata.__setattr__(name, value)
        return metadata

    def load_zip(self, filename) :
        keys1 = [#stuff needed to origanise the data
                 ('width', 'n_energy', int),
                 ('height', 'n_x', int),
                 ('depth', 'n_y', int),
                 ('first_full', 'first_energy', int),
                 ('last_full', 'last_energy', int),
                 ('widthoffset', 'start_energy', float),
                 ('widthdelta', 'step_energy', float),
                 ('heightoffset', 'start_x', float),
                 ('heightdelta', 'step_x', float),
                 ('depthoffset', 'start_y', float),
                 ('depthdelta', 'step_y', float)
                ]

        # Load the zipfile
        with zipfile.ZipFile(filename, 'r') as z :
            # Get the created filename from the viewer
            with z.open('viewer.ini') as viewer :
                file_id = self.read_viewer(viewer)
            # Get most metadata from a metadata file
            with z.open('Spectrum_' + file_id + '.ini') as metadata_file :#not much in here
                M = self.read_metadata(keys1, metadata_file)
            # Get additional metadata from a second metadata file...
            with z.open(file_id + '.ini') as metadata_file2 :
                M2 = self.read_metadata(self.meta_keys, metadata_file2)
            # Extract the binary data from the zipfile
            with z.open('Spectrum_' + file_id + '.bin') as f :
                data_flat = np.frombuffer(f.read(), dtype='float32')
        # Put the data back into its actual shape
        data = np.reshape(data_flat, (int(M.n_y), int(M.n_x), int(M.n_energy)))
        # Cut off unswept region
        data = data[:,:,M.first_energy:M.last_energy+1]
        # Put into shape (energy, other angle, angle along analyzer)
        data = np.moveaxis(data, 2, 0)

        # Create axes
        xscale = start_step_n(M.start_x, M.step_x, M.n_x)
        yscale = start_step_n(M.start_y, M.step_y, M.n_y)
        energies = start_step_n(M.start_energy, M.step_energy, M.n_energy)
        energies = energies[M.first_energy:M.last_energy+1]

        metadata = {}
        for key,name,type in self.meta_keys:
            metadata[name] = vars(M2)[name]

        res = Namespace(
            data = data,
            xscale = xscale,
            yscale = yscale,
            zscale = energies,
            metadata = metadata
        )
        return res

    @staticmethod
    def read_viewer(viewer) :
        """ Extract the file ID from a SIS-ULTRA deflector mode output file. """
        for line in viewer.readlines() :
            l = line.decode('UTF-8')
            if l.startswith('name') :
                # Make sure to split off unwanted whitespace
                return l.split('=')[1].split()[0]

    def load_from_ibw(self, filename) :
        wave = binarywave.load(filename)['wave']
        data = np.array([wave['wData']])

        data = np.swapaxes(data, 1, 2)#make it standard for my program that energy is on x, angle no y

        #print('note',wave['note'])
        #print('data_units',wave['data_units'])
        #print('dimension_units',wave['dimension_units'])

        # The `header` contains some metadata
        header = wave['wave_header']
        nDim = header['nDim']
        steps = header['sfA']
        starts = header['sfB']

        # Construct the x and y scales from start, stop and n
        yscale = start_step_n(starts[0], steps[0], nDim[0])
        xscale = start_step_n(starts[1], steps[1], nDim[1])

        # Convert `note`, which is a bytestring of ASCII characters that
        # contains some metadata, to a list of strings
        note = wave['note']
        note = note.decode('ASCII').split('\r')

        # Now the extraction fun begins. Most lines are of the form
        # `Some-kind-of-name=some-value`
        M2 = dict()
        for line in note :
            # Split at '='. If it fails, we are not in a line that contains
            # useful information
            try :
                name, val = line.split('=')
            except ValueError :
                continue
            # Put the pair in a dictionary for later access
            M2.update({name: val})

        # NOTE Unreliable hv
        #metadata['Excitation Energy'] = [float(metadata['Excitation Energy'])]
        metadata = {}
        for key,name,type in self.meta_keys:
            metadata[name] = M2[key]

        res = Namespace(
                data = data,
                xscale = yscale,
                yscale = xscale,
                zscale = None,
                angles = xscale,
                theta = 0,
                phi = 0,
                E_b = 0,
                metadata = metadata)
        return res

class Bloch(Data_loader):
    def __init__(self,data_tab):
        super().__init__(data_tab)
        self.orientation = 'vertical'
        self.meta_keys = [#the metadata to show in GUI: it will show in this order with the name accotidng yo second column
                        ('Date', 'Date', str),
                        ('Time', 'Time', str),
                        ('Excitation Energy', 'hv', float),
                        ('A', 'azimuth', float),
                        ('P', 'polar', float),
                        ('T', 'tilt', float),
                        ('X', 'X', float),
                        ('Y', 'Y', float),
                        ('Z', 'Z', float),
                        ('Pass Energy', 'Pass Energy', int),
                        ('Number of Sweeps', 'Number of Sweeps', int),
                        ('Acquisition Mode', 'Acquisition Mode', str),
                        ('Center Energy', 'Center Energy', float),
                        ('Low Energy', 'Low Energy', float),
                        ('High Energy', 'High Energy', float),
                        ('Energy Step', 'Energy Step', float)
                        #('Thetay_StepSize', 'Thetay_StepSize', float),
                    #    ('Comments', 'Comments', str)
                        ]#acquisition_mode

    def load_data(self, filename) :
        if filename.endswith('ibw') :
            return self.load_from_ibw(filename)
        elif filename.endswith('zip') :
            return self.load_zip(filename)
        else:
            return None

class I05(Data_loader):
    def __init__(self,data_tab):
        super().__init__(data_tab)
        self.orientation = 'vertical'
        self.meta_keys = [#the metadata to show in GUI: it will show in this order with the name accotidng yo second column
                        ('Time', 'Time', str),
                        ('Excitation Energy', 'hv', float),
                        ('saazimuth', 'azimuth', float),
                        ('sapolar', 'polar', float),
                        ('satilt', 'tilt', float),
                        ('sax', 'X', float),
                        ('say', 'Y', float),
                        ('saz', 'Z', float),
                        ('pass_energy', 'Pass Energy', int),
                        ('number_of_frames', 'Number of Sweeps', int),
                        ('acquisition_mode', 'Acquisition Mode', str),
                        ('kinetic_energy_center', 'Center Energy', float),
                        ('kinetic_energy_start', 'Low Energy', float),
                        ('kinetic_energy_end', 'High Energy', float),
                        #('Energy Step', 'Energy Step', float)
                        #('Thetay_StepSize', 'Thetay_StepSize', float),
                    #    ('Comments', 'Comments', str)
                        ]#acquisition_mode

    def load_data(self, filename) :
        if filename.endswith('nxs') :
            return self.load_from_nxs(filename)
        else:
            return None

    def load_from_nxs(self, filename) :
        # Read file with h5py reader

        infile = h5py.File(filename, 'r')
        data = np.array(infile['/entry1/analyser/data']).T
        angles = np.array(infile['/entry1/analyser/angles'])
        energies = np.array(infile['/entry1/analyser/energies'])
        hv = np.array(infile['/entry1/instrument/monochromator/energy'])

        if len(energies.shape)==2:#I have added, needed for new data
            energies = energies[0]

        zscale = energies
        yscale = angles

        # Check if we have a scan
        if data.shape[2] == 1 :
            xscale = energies
            zscale = np.array([0])
            data = data.T
        else:

            # Otherwise, extract third dimension from scan command
            command = infile['entry1/scan_command'][()].decode("utf-8")#addeed .decode("utf-8")

            # Special case for 'pathgroup'
            if command.split()[1] == 'pathgroup' :
                #self.print_m('is pathgroup')
                # Extract points from a ([polar, x, y], [polar, x, y], ...)
                # tuple
                points = command.split('(')[-1].split(')')[0]
                tuples = points.split('[')[1:]
                xscale = []
                for t in tuples :
                    point = t.split(',')[0]
                    xscale.append(float(point))
                xscale = np.array(xscale)

                # Now, if this was a scan with varying centre_energy, the
                # zscale contains a list of energies...
                # for now, just take the first one
#                zscale = zscale[0]

            # Special case for 'scangroup'
            elif command.split()[1] == 'scan_group':

                #self.print_m('is scan_group')
                # Extract points from a ([polar, x, y], [polar, x, y], ...)
                # tuple
                #print(command.split(','))

                points = command.split('((')[-1].split('))')[0]
                points = ' (' + points + ')'#changed here from '((' + points + '))'

                #added this stuff
                xscale = []
                for s in list(points.split(",")):
                    if s[1] == '(':
                        xscale.append(float(s[2:-2]))
                xscale = np.array(xscale)

                #xscale = np.array(ast.literal_eval(points))[:,0]#changed, commenetd this one

                # Now, if this was a scan with varying centre_energy, the
                # zscale contains a list of energies...
                # for now, just take the first one
                #zscale = zscale[0]

           # "Normal" case
            else :
                start_stop_step = command.split()[2:5]
                start, stop, step = [float(s) for s in start_stop_step]
                xscale = np.arange(start, stop+0.5*step, step)

        # What we usually call theta is tilt in this beamline
        theta = infile['entry1/instrument/manipulator/satilt'][0]
        phi = infile['entry1/instrument/manipulator/sapolar'][0]

        # Take the mean of the given binding energies as an estimate
        try :
            E_b = -np.mean(infile['entry1/analyser/binding_energies'])
        except KeyError :
            E_b = -np.mean(infile['entry1/analyser/energies'])

        M2 = {}
        M2['Time'] = np.array(infile['/entry1/start_time'])
        M2['Excitation Energy'] = hv[0]#hv is a list
        for position in np.array(infile['/entry1/instrument/manipulator']):
            M2[position] = np.array(infile['/entry1/instrument/manipulator/'+position])[0]
        for ana in np.array(infile['/entry1/instrument/analyser']):
            M2[ana] = np.array(infile['/entry1/instrument/analyser/'+ana])

        metadata = {}
        for key,name,type in self.meta_keys:
            metadata[name] = M2[key]

        res = Namespace(
           data = data,
           xscale = xscale,
           yscale = yscale,
           zscale = zscale,
           angles = angles,
           theta = theta,
           phi = phi,
           E_b = E_b,
           metadata = metadata
        )
        return res

class URANOS(Data_loader):
    def __init__(self,data_tab):
        super().__init__(data_tab)
        self.orientation = 'vertical'
        self.meta_keys = [#the metadata to show in GUI
                ('Date', 'Date', str),
                ('Time', 'Time', str),
                ('Excitation Energy', 'hv', float),
                ('R1', 'polar', float),
                ('R3', 'tilt', float),
                ('X', 'X', float),
                ('Y', 'Y', float),
                ('Z', 'Z', float),
                ('Pass Energy', 'Pass Energy', int),
                ('Number of Sweeps', 'Number of Sweeps', int),
                ('Acquisition Mode', 'Acquisition Mode', str),
                ('Center Energy', 'Center Energy', float),
                ('Low Energy', 'Low Energy', float),
                ('High Energy', 'High Energy', float),
                ('Energy Step', 'Energy Step', float)
                #('Thetay_StepSize', 'Thetay_StepSize', float),
                #('Comments', 'Comments', str)
                ]

    def load_data(self, filename) :
        if filename.endswith('ibw') :
            return self.load_from_ibw(filename)
        elif filename.endswith('zip') :
            return self.load_zip(filename)
        else:
            return None

class SIS(Data_loader):
    def __init__(self,data_tab):
        super().__init__(data_tab)
        self.orientation = 'horizontal'
        self.min_cuts_for_map = 10# Number of cuts that need to be present to assume the data as a map instead of a series of cuts
        self.meta_keys = [('Excitation Energy', 'hv', float)]#zip files

        #h5 files
        self.meta_keys2 = ['Acquisition Mode','Date Created','Excitation Energy (eV)', 'Pass Energy (eV)','Specified Number of Sweeps']
        self.meta_keys3 = [ 'Temperature A', 'Temperature B','Exit Slit', 'Phi', 'Theta', 'Tilt', 'X', 'Y', 'Z']

    def load_data(self, filename) :
        if filename.endswith('h5') :
            return self.load_h5(filename)
        elif filename.endswith('zip') :
            return self.load_zip(filename)
        elif filename.endswith('ibw') :
            return self.load_from_ibw(filename)
        else:
            return None

    def load_h5(self, filename) :
        """ Load and store the full h5 file and extract relevant information. """
        # Load the hdf5 file
        self.datfile = h5py.File(filename, 'r')
        # Extract the actual dataset and some metadata
        h5_data = self.datfile['Electron Analyzer/Image Data']
        attributes = h5_data.attrs

        # Convert to array and make 3 dimensional if necessary
        shape = h5_data.shape
        # Access data chunk-wise, which is much faster.
        # This improvement has been contributed by Wojtek Pudelko and makes data
        # loading from SIS Ultra orders of magnitude faster!
        if len(shape) == 3:
            data = np.zeros(shape)
            for i in range(shape[2]):
                data[:, :, i] = h5_data[:, :, i]
        else:
            data = np.array(h5_data)
        # How the data needs to be arranged depends on the scan type: cut,
        # map, hv scan or a sequence of cuts
        # Case cut
        if len(shape) == 2 :
            x = shape[0]
            y = shape[1]
            # Make data 3D
            data = data.reshape(1, x, y)
#            N_E = y
            N_E = 1
            # Extract the limits
            xlims = attributes['Axis1.Scale']
            ylims = attributes['Axis0.Scale']
#            elims = ylims
            elims = [1, 1]
        # shape[2] should hold the number of cuts. If it is reasonably large,
        # we have a map. Otherwise just a sequence of cuts.
        # Case map
        elif shape[2] > self.min_cuts_for_map :
            #self.print_m('Is a map?')
            x = shape[1]
            y = shape[2]
            N_E = shape[0]
            # Extract the limits
            xlims = attributes['Axis2.Scale']
            ylims = attributes['Axis1.Scale']
            elims = attributes['Axis0.Scale']
        # Case sequence of cuts
        else :
            x = shape[0]
            y = shape[1]
            N_E = y
            z = shape[2]
            # Reshape data
            #new_data = np.zeros([z, x, y])
            #for i in range(z) :
            #    cut = data[:,:,i]
            #    new_data[i] = cut
            #data = new_data
            data = np.rollaxis(data, 2, 0)
            # Extract the limits
            xlims = attributes['Axis1.Scale']
            ylims = attributes['Axis0.Scale']
            elims = ylims

        # Construct x, y and energy scale (x/ylims[1] contains the step size)
        xscale = start_step_n(*xlims, y)
        yscale = start_step_n(*ylims, x)
        energies = start_step_n(*elims, N_E)
#        xscale = self.make_scale(xlims, y)
#        yscale = self.make_scale(ylims, x)
#        energies = self.make_scale(elims, N_E)

        # Extract some data for ang2k conversion
        manipulator = self.datfile['Other Instruments']


        theta = manipulator['Theta'][0]
        #theta = metadata['Tilt'][0]
        phi = manipulator['Phi'][0]
        hv = attributes['Excitation Energy (eV)']
        angles = xscale
        E_b = min(energies)

        metadata = {}
        for key in self.meta_keys2:
            metadata[key] = attributes[key]
        for key in self.meta_keys3:
            metadata[key] = manipulator[key][0]

        res = Namespace(
               data = data,
               xscale = xscale,
               yscale = yscale,
               zscale = energies,
               angles = angles,
               theta = theta,
               phi = phi,
               E_b = E_b,
               metadata = metadata
        )
        return res
