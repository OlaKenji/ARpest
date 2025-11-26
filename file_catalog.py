import tkinter as tk
from tkinter import ttk

import file_handler

class File_catalog():
    def __init__(self, data_handler):
        self.data_handler = data_handler
        self.file_catalog()
        for index, data in enumerate(self.data_handler.files):
            self.append_files(data.name,index + 1)
        self.update(self.data_handler.index)
        self.file_handler = file_handler.File_handler(self)
        self.define_bottons()

    def file_catalog(self):#make a box containig data
        self.catalog = tk.ttk.Treeview(self.data_handler.overview.tab,columns=  'Data',show='headings',height=2)
        verscrlbar = tk.ttk.Scrollbar(self.data_handler.overview.tab,orient ="vertical",command = self.catalog.yview)
        self.catalog.heading('Data')
        self.catalog.configure(yscrollcommand = verscrlbar.set)
        self.catalog.place(x = 890, y = 695, width=300,height=150)
        self.catalog.bind('<Button-1>', self.data_handler.select_file)#should only be activated when the files have neen loaded?

    def update(self, index):
        child_id = self.catalog.get_children()[index]#set the focus on the new item
        self.catalog.focus(child_id)
        self.catalog.selection_set(child_id)

    def clean(self):
        for item in self.catalog.get_children():
              self.catalog.delete(item)

    def update_catalog(self):
        self.clean()
        for index, data in enumerate(self.data_handler.files):#file objects
            self.catalog.insert('',tk.END,values=data.name, iid = index+1)
        self.update(self.data_handler.index)

    def append_files(self,file,index):#insert the name into the catalog
        idx = file.rfind('/') + 1
        name = file[idx:]
        self.catalog.insert('',tk.END,values=name,iid = index)
        self.update(0)#should it be 0 or self.data_handler.index?

    def define_bottons(self):#called frin init
        button_calc = tk.ttk.Button(self.data_handler.overview.tab, text="Load data", command = self.file_handler.load_data)#the botton to add data (e.g. several measurement but divided into several files)
        button_calc.place(x = 1200, y = 710)

        button_calc = tk.ttk.Button(self.data_handler.overview.tab, text="Add data", command = self.file_handler.add_data)#the botton to add data (e.g. several measurement but divided into several files)
        button_calc.place(x = 1200, y = 740)

        button = tk.ttk.Button(self.data_handler.overview.tab, text="combine data", command = self.file_handler.combine_data)#kz
        button.place(x = 1200, y = 770)

        button_calc = tk.ttk.Button(self.data_handler.overview.tab, text="Delete data", command = self.file_handler.delete_file)
        button_calc.place(x = 1200, y = 810)
