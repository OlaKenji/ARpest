import tkinter as tk
from tkinter import ttk

import data_loader

class Data_handler():#contains the stack of data as a list
    def __init__(self, overivew, data):
        self.sub_tab = overivew

        if isinstance(data,list):#if okf file -> old file: contains meta and x,y,z,data
            #self.data_stack = [File(data['data_stack'])]
            self.index = data[0].save_dict.get('data_stack_index',[0,0])#[0] points to state, [1] points to file

            self.data_stack = data.copy()#a list of file objects
            self.data = self.data_stack[0]#data.copy()#copy all dict to self.data
            #self.data.pop('data_stack')#remove the x,y,z,data stuff (File object should have these)
            self.organise_data()
        else:#if normal file -> first time
            self.data_stack = [File(data, self.sub_tab.data_tab.name)]
            self.data = self.data_stack[0]#a file object
            self.index = [0,0]

        self.define_bottons()
        self.state_catalog()

    def state_catalog(self):#state holders
        self.catalog = tk.ttk.Treeview(self.sub_tab.tab,columns='States',show='headings',height=2)
        verscrlbar = tk.ttk.Scrollbar(self.sub_tab.tab,orient ="vertical",command = self.catalog.yview)
        self.catalog.heading('States')
        self.catalog.configure(yscrollcommand = verscrlbar.set)
        self.catalog.place(x = 890, y = 520, width=300,height=100)
        self.update_catalog()
        self.catalog.bind('<Button-1>', self.select_state)#should only be activated when the files have neen loaded?

    def update_catalog(self):
        for item in self.catalog.get_children():
              self.catalog.delete(item)
        for index, state in enumerate(self.data.states):
            self.append_state(state,index+1)

        child_id = self.catalog.get_children()[self.data.index]#set the focus on the new item
        self.catalog.focus(child_id)
        self.catalog.selection_set(child_id)

    def append_state(self,name, index = 1):
        self.catalog.insert('',tk.END,values=name, iid = index)

    def select_state(self,event):#called when pressing an item in the catalog
        column = self.catalog.identify_row(event.y)#where did you click?
        index = int(column[-1]) - 1
        self.data_stack[self.index[1]].set_state(index)
        self.organise_data()
        self.sub_tab.figure_handeler.new_stack()

    def select_file(self,event):#called when pressing an item in the catalog
        column = self.sub_tab.data_catalog.catalog.identify_row(event.y)#where did you click?
        index = int(column[-1]) - 1
        self.index[1] = index
        self.organise_data()
        self.sub_tab.figure_handeler.new_stack()
        self.update_catalog()

    def add_file(self,data, file):#called from load data bottom in data_catalog: it adds new files
        idx = file.rfind('/') + 1
        name = file[idx:]
        self.data_stack.append(File(data[0], name))
        self.index[1] += 1
        self.organise_data()
        self.sub_tab.figure_handeler.new_stack()
        self.update_catalog()
        self.sub_tab.logbook.add_log(self.data_stack[-1])

    def add_stack(self,data):#new states, should be called after new operations
        self.data_stack[self.index[1]].append(data)
        self.index[0] += 1
        self.organise_data()
        self.sub_tab.figure_handeler.new_stack()

    def organise_data(self):
        self.data = self.data_stack[self.index[1]]#a file object

    def define_bottons(self):
        button_calc = tk.ttk.Button(self.sub_tab.tab, text = "delete stack", command = self.delete_stack)#which figures shoudl have access to this?
        button_calc.place(x = 1200, y = 540)

    def delete_stack(self):
        self.data.remove_state()
        self.update_catalog()
        self.organise_data()
        self.sub_tab.figure_handeler.new_stack()

class File():#the data onject, contains the list of data and the rellavant poitners
    def __init__(self, data, name):
        self.data = [data]
        self.index = 0
        self.states = ['raw']
        self.save_dict = {}
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

    def save(self,dict):#
        self.save_dict.update(dict)
