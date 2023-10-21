import tkinter as tk
from tkinter import ttk
import numpy as np
import data_loader

class File_handler():
    def __init__(self, data_catalog):
        self.data_catalog = data_catalog

    def delete_file(self):
        if self.data_catalog.overview.data_handler.index[1] == 0: return#protect original
        self.data_catalog.overview.data_handler.data_stack.pop(self.data_catalog.overview.data_handler.index[1])
        self.data_catalog.overview.data_handler.index[1] -= 1
        self.data_catalog.update_catalog()

        self.data_catalog.overview.logbook.clean()
        for data in self.data_catalog.overview.data_handler.data_stack:
            self.data_catalog.overview.logbook.add_log(data)
        self.data_catalog.overview.data_handler.organise_data()
        self.data_catalog.overview.data_handler.update_catalog()

    def load_data(self):#called when pressing bottom
        files = tk.filedialog.askopenfilenames(initialdir=self.data_catalog.overview.data_tab.gui.start_path ,title='data')
        if not files: return
        loadded_data = getattr(data_loader, self.data_catalog.overview.data_tab.gui.start_screen.instrument.get())(self.data_catalog.overview.data_tab)#make an object based on string
        for index, file in enumerate(files):
            data = loadded_data.load_data(file)
            self.data_catalog.overview.data_handler.add_file(data, file)
            self.data_catalog.append_files(file,len(self.data_catalog.overview.data_handler.data_stack))

    def add_data(self):
        indices = self.data_catalog.catalog.selection()
        dict = self.data_catalog.overview.data_handler.data.data[-1].copy()
        for num, index in enumerate(indices):
            if num == 0: continue
            dict['data'] = dict['data'] + self.data_catalog.overview.data_handler.data_stack[num].data[0]['data']

        dict['data'] = dict['data']/(num+1)
        self.data_catalog.overview.data_handler.data.add_state(dict,'added')
        self.data_catalog.overview.data_handler.append_state('k_convert', len(self.data_catalog.overview.data_handler.data.states))
        self.data_catalog.overview.data_handler.update_catalog()
        self.data_catalog.overview.figure_handeler.new_stack()

    def combine_data(self):#combining and putting the data in the data catalog: photon energy as x, angle as  y, kintex energy as z, intensity as data (3D)
        indices = self.data_catalog.catalog.selection()
        hv = []
        dict = self.data_catalog.overview.data_handler.data.data[-1].copy()
        for num, index in enumerate(indices):
            scan_data = self.data_catalog.overview.data_handler.data_stack[num]#file object

            #hv.append(scan_data['metadata']['hv'])#the photon energy
            hv.append(64+2*num)
            if num == 0:
                int = np.atleast_3d(np.transpose(scan_data.data[0]['data']))
            else:
                int = np.append(int,np.atleast_3d(np.transpose(scan_data.data[0]['data'])),axis=2)

        scan_data.data[0]['metadata']['hv'] = hv
        new_data = {'xscale':np.array(hv), 'yscale':scan_data.data[0]['yscale'],'zscale':scan_data.data[0]['xscale'],'data':int,'metadata':scan_data.data[0]['metadata']}
        tab = self.data_catalog.overview.data_tab.append_tab(new_data)
