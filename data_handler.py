import tkinter as tk
from tkinter import ttk

import file_catalog, state_catalog

class Data_handler():#contains the stack of data as a list
    def __init__(self, overivew, data):
        self.overview = overivew

        if len(data.keys()) <= 2:#if okf file -> old file: contains meta and x,y,z,data
            self.index = data['global'].get('data_stack_index',0)
            self.files = data['files'].copy()#a list of file objects
            self.file = self.files[0]
            self.organise_data()
            self.save_dict = data['global']
        else:#if normal file -> first time
            self.files = [File(data, self.overview.data_tab.name)]
            self.file = self.files[0]#a file object
            self.index = 0
            self.save_dict = {}

        self.file_catalog = file_catalog.File_catalog(self)
        self.state_catalog = state_catalog.State_catalog(self)

    def select_state(self,event):#called when pressing an item in the catalog
        column = self.state_catalog.catalog.identify_row(event.y)#where did you click?
        index = int(column[-1]) - 1
        self.files[self.index].set_state(index)
        self.organise_data()
        self.overview.figure_handeler.new_stack()

    def select_file(self,event):#called when pressing an item in the catalog
        column = self.file_catalog.catalog.identify_row(event.y)#where did you click?
        self.file_catalog.update(int(column) -1)#update the tree

        curItem = self.file_catalog.catalog.focus()#get the focus item
        self.index = int(curItem) - 1
        self.organise_data()
        self.overview.figure_handeler.new_stack()
        self.file_catalog.update(self.index)
        self.state_catalog.update_catalog()

    def add_file(self,data, file):#called from load data bottom in data_catalog: it adds new files
        idx = file.rfind('/') + 1
        name = file[idx:]
        if any(isinstance(i, list) for i in data):#if okf file: it checks if it is a nested list
            overview, file = 0, 0
            data[overview][file].name = name
            self.files.append(data[overview][file])
        else:#normal file
            self.files.append(File(data[0], name))

        self.index = len(self.files)-1
        self.organise_data()
        self.overview.figure_handeler.new_stack()
        self.file_catalog.update_catalog()
        self.overview.logbook.add_log(self.files[-1])

    def organise_data(self):
        self.file = self.files[self.index]#a file object

    def delete_state(self):
        self.file.remove_state()
        self.state_catalog.update_catalog()
        self.organise_data()
        self.overview.figure_handeler.new_stack()

class File():#the data onject, contains the list of data and the rellavant poitners
    def __init__(self, data, name):
        self.data = [data]
        self.index = 0
        self.states = ['raw']
        self.name = name

    def remove_state(self):
        if self.index == 0: return#protect raw
        self.data.pop(self.index)
        self.states.pop(self.index)
        self.index -= 1

    def get(self, key, default):
        return self.data[self.index].get(key, default)

    def set_data(self, key, data):
        self.data[self.index][key] = data

    def get_data(self, key):
        return self.data[self.index][key]

    def add_state(self,data,name):
        self.data.append(data)
        self.next_state()
        self.states.append(name)

    def next_state(self):
        self.index += 1

    def previous_state(self):
        self.index -= 1

    def set_state(self,index):
        self.index = index
