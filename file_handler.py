import tkinter as tk
from tkinter import ttk
import numpy as np
import data_loader

class File_handler():
    def __init__(self, file_catalog):
        self.file_catalog = file_catalog

    def delete_file(self):
        if self.file_catalog.data_handler.index == 0: return#protect original
        self.file_catalog.data_handler.files.pop(self.file_catalog.data_handler.index)
        self.file_catalog.data_handler.index -= 1
        self.file_catalog.update_catalog()

        self.file_catalog.data_handler.overview.logbook.clean()
        for data in self.file_catalog.data_handler.files:
            self.file_catalog.data_handler.overview.logbook.add_log(data)
        self.file_catalog.data_handler.organise_data()
        self.file_catalog.update_catalog()

    def load_data(self):#called when pressing bottom
        files = tk.filedialog.askopenfilenames(initialdir=self.file_catalog.data_handler.overview.data_tab.gui.start_path ,title='data')
        if not files: return
        loadded_data = getattr(data_loader, self.file_catalog.data_handler.overview.data_tab.gui.start_screen.instrument.get())(self.file_catalog.data_handler.overview.data_tab)#make an object based on string
        for index, file in enumerate(files):
            data = loadded_data.load_data(file)
            self.file_catalog.data_handler.add_file(data, file)

    def add_data(self):
        indices = self.file_catalog.catalog.selection()
        dict = self.file_catalog.data_handler.file.data[0].copy()#the raw
        dict['data'] = dict['data'] - dict['data']#0 them
        for num, index in enumerate(indices):
            dict['data'] = dict['data'] + self.file_catalog.data_handler.files[num].data[0]['data']#the raw

        dict['data'] = dict['data']/(num+1)
        self.file_catalog.data_handler.add_file([dict], '/added')#add a new file

    def combine_data(self):#combining and putting the data in the data catalog: photon energy as x, angle as  y, kintex energy as z, intensity as data (3D)
        indices = self.file_catalog.catalog.selection()
        hv = []
        dict = self.file_catalog.data_handler.file.data[-1].copy()
        for num, index in enumerate(indices):
            scan_data = self.file_catalog.data_handler.files[num]#file object

            hv.append(scan_data.data[0]['metadata']['hv'])#the photon energy
            #hv.append(64+2*num)
            if num == 0:
                int = np.atleast_3d(np.transpose(scan_data.data[0]['data']))
            else:
                int = np.append(int,np.atleast_3d(np.transpose(scan_data.data[0]['data'])),axis=2)

        #scan_data.data[0]['metadata']['hv'] = hv
        new_data = {'xscale':np.array(hv), 'yscale':scan_data.data[0]['yscale'],'zscale':scan_data.data[0]['xscale'],'data':int,'metadata':scan_data.data[0]['metadata']}
        tab = self.file_catalog.data_handler.overview.data_tab.append_tab(new_data)
