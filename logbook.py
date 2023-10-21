import tkinter as tk
from tkinter import ttk

class Logbook():
    def __init__(self, sub_tab):
        self.sub_tab = sub_tab
        self.logbook()
        self.define_update_logbook()

    def logbook(self):
        columns, data = [], []
        for key in self.sub_tab.data_handler.data.get_data('metadata'):
            columns.append(key)
            data.append(self.sub_tab.data_handler.data.get_data('metadata')[key])

        self.tree = tk.ttk.Treeview(self.sub_tab.tab, columns = columns, show = 'headings', height = 2)

        for texts in columns:
            self.tree.heading(texts,text=texts)
            self.tree.column(texts,width=100,stretch=False)

        for data in self.sub_tab.data_handler.data_stack:
            self.add_log(data)

        self.tree.place(x = 890, y = 0, width=610)
        self.tree.bind("<Double-1>",self.update_logbook)#, lambda e, tr = self.tree: tr.tk.call(tr._w,'xview', 'scroll', 1, 'units')
        self.tree.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self,test1):
        self.tree.xview(tk.SCROLL,1, "units")
        self.tree.yview(tk.SCROLL,1, "units")

    def clean(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def add_log(self,data):#called from add_file in dara_handeler
        values = []
        for key in data.get_data('metadata'):
            values.append(data.get_data('metadata')[key])
        self.tree.insert('',tk.END,values=values)

    #the douilble cliking part
    def define_update_logbook(self):
        self.log_entry = tk.ttk.Entry(self.sub_tab.tab, width= 3)#
        self.log_entry.place(x = 1460, y = 60)

    def update_logbook(self,event):
        column = self.tree.identify_column(event.x)#where did you click?
        value = self.log_entry.get()
        if value == '': return#if nothing there, do nothing
        self.tree.set('log', column = column, value = value)
        #self.sub_tab.data_handler.data.get_data('metadata') = self.tree.set('log')
