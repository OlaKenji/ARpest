import tkinter as tk
from tkinter import ttk

class State_catalog():#contains the stack of data as a list
    def __init__(self, data_handler):
        self.data_handler = data_handler
        self.define_bottons()
        self.state_catalog()

    def state_catalog(self):#state holders
        self.catalog = tk.ttk.Treeview(self.data_handler.overview.tab,columns='States',show='headings',height=2)
        verscrlbar = tk.ttk.Scrollbar(self.data_handler.overview.tab,orient ="vertical",command = self.catalog.yview)
        self.catalog.heading('States')
        self.catalog.configure(yscrollcommand = verscrlbar.set)
        self.catalog.place(x = 890, y = 520, width=300,height=100)
        self.update_catalog()
        self.catalog.bind('<Button-1>', self.data_handler.select_state)#should only be activated when the files have neen loaded?

    def update_catalog(self):
        for item in self.catalog.get_children():
              self.catalog.delete(item)
        for index, state in enumerate(self.data_handler.file.states):
            self.append_state(state,index+1)

        child_id = self.catalog.get_children()[self.data_handler.file.index]#set the focus on the new item
        self.catalog.focus(child_id)
        self.catalog.selection_set(child_id)

    def append_state(self,name, index = 1):
        self.catalog.insert('',tk.END,values=name, iid = index)

    def define_bottons(self):
        button_calc = tk.ttk.Button(self.data_handler.overview.tab, text = "delete stack", command = self.data_handler.delete_state)#which figures shoudl have access to this?
        button_calc.place(x = 1200, y = 540)
