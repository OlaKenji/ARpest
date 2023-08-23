import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.pyplot import get_cmap

import tkinter as tk
import numpy as np
import json
from argparse import Namespace

import processing, cursor, data_loader

class Functions():#figure functionality not being used
    def __init__(self):
        pass

    def subtract_BG(self):#the BG botton calls it
        pass

    #not in use
    def define_normalise(self):
        self.define_norm_entry()
        button_calc = tk.Button(self.sub_tab.tab, text="Normalise", command = self.normalise)
        offset = [200,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def define_norm_entry(self):
        self.e1 = tk.Entry(self.sub_tab.tab,width=2)#the step size
        offset = [300,0]
        self.e1.place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])
        self.e1.insert(0, 1)#default value 1

    def normalise(self):
        norm = float(self.e1.get())
        self.int = self.int/norm
        self.draw()

class Figure(Functions):
    def __init__(self,figure_handeler,pos):
        self.figure_handeler = figure_handeler
        self.sub_tab = figure_handeler.data_tab#analysis or overview
        self.pos = pos
        self.label = ['x','y']
        self.init_data()
        self.original_int = self.int

        self.colour_limit()
        self.define_canvas()
        self.define_export()
        self.define_mouse()
        self.draw()
        #self.define_normalise()

    def init_data(self):
        self.intensity()
        self.sort_data()

    def define_canvas(self):
        self.fig = plt.Figure(figsize = [4.45,4.3])
        self.size = self.fig.get_size_inches()*self.fig.dpi
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(top=0.93,left=0.15,right=0.97)

        self.ax.set_yticklabels([])#to make the blank BG without any axis numbers
        self.ax.set_xticklabels([])
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        self.canvas = FigureCanvasTkAgg(self.fig, master = self.sub_tab.tab)
        self.canvas.draw()

        offset = [0,0]
        self.canvas.get_tk_widget().place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])#grid(row=1,column=self.column)
        self.blank_background = self.fig.canvas.copy_from_bbox(self.ax.get_figure().bbox)#including the axis

    def mouse_range(self):#used for crusor
        self.xlimits = [np.nanmin(self.data[0]), np.nanmax(self.data[0])]
        self.ylimits = [np.nanmin(self.data[1]), np.nanmax(self.data[1])]

    def define_mouse(self):#called in init and from processing
        self.mouse_range()
        self.cursor = cursor.Auto_cursor(self)

        self.canvas.get_tk_widget().bind( "<Motion>", self.cursor.on_mouse_move)
        self.canvas.get_tk_widget().bind( "<Button-1>", self.cursor.on_mouse_click)#left click
        self.canvas.get_tk_widget().bind( "<Button-2>", self.right_click)#right click
        self.canvas.get_tk_widget().bind( "<Double-Button-1>", self.double_click)#double click

    def define_export(self):
        button_calc = tk.ttk.Button(self.sub_tab.tab, text="Export", command = self.export)
        offset = [320,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def export(self):
        export_data = {'x':self.data[0].tolist(), 'y':self.data[1].tolist(), 'z':self.int.tolist()}
        path = self.sub_tab.data_tab.gui.start_path + '/' + self.sub_tab.data_tab.name
        with open(path+"_exported.json", "w") as outfile:
            json.dump(export_data, outfile)

    def define_add_data(self):
        button_calc = tk.ttk.Button(self.sub_tab.tab, text="Add data", command = self.add_data)
        offset = [80,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def add_data(self):
        files = tk.filedialog.askopenfilenames(initialdir=self.sub_tab.data_tab.gui.start_path ,title='data')
        for file in files:
            loadded_data = getattr(data_loader, self.sub_tab.data_tab.gui.start_screen.instrument.get())(self.sub_tab)#make an object based on string
            data = loadded_data.load_data(file)
            self.data[-1] = self.data[-1] + data.data

        self.data[-1] = self.data[-1]/(len(files)+1)
        self.intensity()
        self.draw()

    def angle_crusor(self):
        self.anglecrusor = cursor.Angle_cursor(self)
        self.anglecrusor.redraw()

    def double_click(self,event):
        pass

    def click(self,pos):
        self.cursor.redraw()

    def right_click(self,event):
        self.sub_tab.data_tab.gui.pop_up()#call gui to make a new window object
        self.plot(self.sub_tab.data_tab.gui.pop.ax)#plot the fraph onto the popup ax
        self.sub_tab.data_tab.gui.pop.pop_canvas.draw()#draw it after plot

    def draw(self):
        self.ax.cla()
        self.plot(self.ax)
        self.set_label()
        self.canvas.draw()
        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def redraw(self):
        self.update_colour_scale()
        self.canvas.restore_region(self.blank_background)
        self.ax.draw_artist(self.graph)
        self.canvas.blit(self.ax.bbox)
        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def int_range(self,index):
        if self.sub_tab.int_range == 0:#if no integrate
            return index, index + 1, 1
        else:#if integrate
            if index-self.sub_tab.int_range < 0:
                index = self.sub_tab.int_range
            start = index - self.sub_tab.int_range
            stop = index + self.sub_tab.int_range + 1
            step = stop - start
            return start, stop, step

    def set_label(self):#called from draw
        self.ax.set_xlabel(self.label[0])
        self.ax.set_ylabel(self.label[1])

    def update_colour_scale(self):#called in redraw
        value = self.sub_tab.operations.color_scale.get()
        self.vmax = np.nanmax(self.int)*int(float(value))/100
        self.graph.set_clim(vmin=self.vmin, vmax=self.vmax)

    def colour_limit(self):#called in init
        self.vmin = np.nanmin(self.int)
        self.vmax = np.nanmax(self.int)

class FS(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)
        self.figures = figure_handeler.figures
        self.tilt =  self.sub_tab.data.metadata['tilt']
        self.define_add_data()

    def init_data(self):
        self.sort_data()
        self.intensity()

    def plot(self,ax):#pcolorfast
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1,cmap=self.sub_tab.cmap, norm = colors.Normalize(vmin = self.vmin, vmax = self.vmax))#FS
        #self.fig.colorbar(self.graph)

    def sort_data(self):
        self.data = [self.sub_tab.data.xscale,self.sub_tab.data.yscale,self.sub_tab.data.zscale,self.sub_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0]-pos[0])
        index1 = difference_array.argmin()

        self.figures['right'].intensity(index1)
        self.figures['right'].plot(self.figures['right'].ax)
        self.figures['right'].redraw()
        self.figures['right'].click(pos)

        difference_array = np.absolute(self.data[1]-pos[1])
        index2 = difference_array.argmin()
        self.figures['down'].intensity(index2)
        self.figures['down'].plot(self.figures['down'].ax)
        self.figures['down'].redraw()
        self.figures['down'].click(pos)

    def intensity(self,z = 0):
        start,stop,step = self.int_range(z)
        self.int = np.nansum(self.data[3][start:stop:1],axis=0)/step#sum(self.data[3][start:stop:1])/step#this takes long tim for sum reason in kz space
        self.colour_limit()

    def define_hv(self):#called from procssing
        return self.data[1], np.array([self.tilt])

    def define_angle2k(self):#called from procssing, convert k
        return self.data[1], self.data[0]

class Band_right(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def subtract_BG(self):#not in use
        difference_array1 = np.absolute(self.data[0] - self.cursor.sta_vertical_line.get_data()[0])
        index1 = difference_array1.argmin()
        bg = np.nanmean(self.int[:,index1:-1],axis=1)#axis = 0is vertical, axis =1 is horizontal means
        self.figure_handeler.figures['center'].int -=  bg[:,None]
        self.figure_handeler.figures['center'].draw()

    def double_click(self,event):#called when doubleclicking
        new_data = Namespace(xscale=self.data[0], yscale=self.data[1],zscale = None,data=np.transpose(np.atleast_3d(self.int),axes=(2, 0, 1)),metadata=self.sub_tab.data.metadata)
        self.sub_tab.data_tab.append_tab(new_data)

    def plot(self,ax):
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band_right

    def intensity(self,y=0):
        start,stop,step = self.int_range(y)
        self.int = []
        for ary in self.figure_handeler.figures['center'].data[3]:
            self.int.append(np.sum(ary[:,start:stop:1],axis=1)/step)
        self.int = np.transpose(self.int)
        self.colour_limit()

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[2],self.figure_handeler.figures['center'].data[1],self.figure_handeler.figures['center'].data[3]]

    def click(self,pos):
        super().click(pos)
        pos = self.cursor.sta_horizontal_line.get_data()

        difference_array1 = np.absolute(self.data[1]-pos[1])
        index1 = difference_array1.argmin()
        self.figure_handeler.figures['corner'].intensity_right(index1)
        #self.figure_handeler.figures['corner'].draw()
        self.figure_handeler.figures['corner'].plot(self.figure_handeler.figures['corner'].ax)
        self.figure_handeler.figures['corner'].redraw()

class Band_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def subtract_BG(self):#not in use
        difference_array1 = np.absolute(self.data[1] - self.cursor.sta_horizontal_line.get_data()[1])
        index1 = difference_array1.argmin()
        bg = np.mean(self.int[index1:len(self.data[1]),:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
        self.int -=  bg
        self.draw()

    def double_click(self,event):#called when doubleclicking
        new_data = Namespace(xscale=self.data[0], yscale=self.data[1],zscale = None,data=np.transpose(np.atleast_3d(self.int),axes=(2, 0, 1)),metadata=self.sub_tab.data.metadata)
        self.sub_tab.data_tab.append_tab(new_data)

    def plot(self,ax):#2D plot
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int,zorder=1,cmap=self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band down

    def intensity(self,y=0):
        start,stop,step=self.int_range(y)
        int = []
        for ary in self.figure_handeler.figures['center'].data[3]:
            int.append(sum(ary[start:stop:1])/step)
        self.int = np.array(int)
        self.colour_limit()

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[0], self.figure_handeler.figures['center'].data[2],self.figure_handeler.figures['center'].data[3]]

    def click(self,pos):
        super().click(pos)
        pos = self.cursor.sta_vertical_line.get_data()
        difference_array1 = np.absolute(self.data[0]-pos[0])
        index1 = difference_array1.argmin()

        self.figure_handeler.figures['corner'].intensity_down(index1)
        #self.figure_handeler.figures['corner'].draw()
        self.figure_handeler.figures['corner'].plot(self.figure_handeler.figures['corner'].ax)
        self.figure_handeler.figures['corner'].redraw()

class DOS_right_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[2],self.int_right]

    def intensity(self,idx=0):
        self.intensity_right(idx)
        self.intensity_down(idx)
        self.int = (self.int_right+self.int_down)*0.5
        self.colour_limit()

    def intensity_right(self,idx=0):
        start,stop,step=self.int_range(idx)
        self.int_right = sum(self.figure_handeler.figures['right'].int[start:stop:1])/step

    def intensity_down(self,idx=0):
        start,stop,step=self.int_range(idx)
        int_down=[]
        for ary in self.figure_handeler.figures['down'].int:
            int_down.append(sum(ary[start:stop:1])/step)
        self.int_down = np.array(int_down)

    def plot(self,ax):#2D plot
        self.graph1 = ax.plot(self.data[0], self.int_right, 'b-',zorder=3)[0]
        self.graph2 = ax.plot(self.data[0], self.int_down, 'r-',zorder=3)[0]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.figure_handeler.figures['center'].data[2]-pos[0])
        index1 = difference_array.argmin()
        self.figure_handeler.figures['center'].intensity(index1)#this is slow for some reason in kz space
        self.figure_handeler.figures['center'].plot(self.figure_handeler.figures['center'].ax)
        self.figure_handeler.figures['center'].redraw()

    def update_colour_scale(self):
        pass

    def redraw(self):
        ymin=min(np.nanmin(self.int_right),np.nanmin(self.int_down))
        ymax=max(np.nanmax(self.int_right),np.nanmax(self.int_down))
        xmin=min(self.data[0])
        xmax=max(self.data[0])

        self.ax.set_xlim([xmin,xmax])
        self.ax.set_ylim([ymin,ymax])

        self.canvas.restore_region(self.blank_background)
        self.ax.draw_artist(self.ax.get_yaxis())
        self.ax.draw_artist(self.ax.get_xaxis())

        self.ax.draw_artist(self.graph1)
        self.ax.draw_artist(self.graph2)

        self.canvas.blit(self.ax.clipbox)

        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

class Band(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)
        self.tilt = self.sub_tab.data.metadata['tilt']
        self.figures = figure_handeler.figures
        self.define_add_data()

    def init_data(self):
        self.sort_data()
        self.intensity()

    def subtract_BG(self):#the BG botton calls it
        if self.sub_tab.operations.checkbox['vertical'].get():#vertical bg subtract
            difference_array1 = np.absolute(self.data[1] - self.cursor.sta_horizontal_line.get_data()[1])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.int[index1:-1,:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
            self.int = self.int - bg
        elif self.sub_tab.operations.checkbox['horizontal'].get():#horizontal bg subtract
            difference_array1 = np.absolute(self.data[0] - self.cursor.sta_vertical_line.get_data()[0])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.int[:,index1:-1],axis=1)#axis = 0is vertical, axis =1 is horizontal means
            int = np.transpose(self.int) - bg
            self.int = np.transpose(int)
        elif self.sub_tab.operations.checkbox['EDC'].get():#EDC bg subtract
            self.int = self.int - self.figures['down'].int[None,:]#subtract the EDC from each row in data

        self.draw()
        self.click([self.cursor.sta_vertical_line.get_data()[0],self.cursor.sta_horizontal_line.get_data()[1]])#update the right and down figures

    def plot(self,ax):#2D plot
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap, norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band
        #ax.set_ylim(74.7, 75.3)

    def sort_data(self):
        self.data = [self.sub_tab.data.xscale, self.sub_tab.data.yscale, self.sub_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0] - pos[0])#subtract for each channel, works.
        index1 = np.argmin(difference_array)
        self.figures['right'].intensity(index1)
        self.figures['right'].draw()

        difference_array = np.absolute(self.data[1] - pos[1])
        index2 = np.argmin(difference_array)
        self.figures['down'].intensity(index2)
        self.figures['down'].draw()

    def intensity(self,y = 0):
        self.int = self.data[-1][0]

    def define_angle2k(self):#called from procssing
        return self.data[1],np.array([self.tilt])

class DOS_right(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        #self.intensity()
        self.data = [self.int,self.figure_handeler.figures['center'].data[1]]

    def intensity(self,x = 0):
        start,stop,step=self.int_range(x)
        int = []
        for ary in self.figure_handeler.figures['center'].int:
            int.append(sum(ary[start:stop:1])/step)
        self.int = np.array(int)
        self.sort_data()

    def plot(self,ax):#2D plot
        self.graph = ax.plot(self.int,self.figure_handeler.figures['center'].data[1])[0]#DOS right

    def update_colour_scale(self):
        pass

class DOS_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        #self.intensity()
        self.data = [self.figure_handeler.figures['center'].data[0],self.int]

    def intensity(self,y=0):
        start,stop,step=self.int_range(y)
        self.int = sum(self.figure_handeler.figures['center'].int[start:stop:1])/step
        #self.int = self.sub_tab.center.int[y]
        self.sort_data()

    def plot(self,ax):#2D plot
        self.graph = ax.plot(self.figure_handeler.figures['center'].data[0], self.int)[0]#DOS down

    def update_colour_scale(self):
        pass
