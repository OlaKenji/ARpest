import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.pyplot import get_cmap

import tkinter as tk
import numpy as np
import json#for the export

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
        self.sub_tab = figure_handeler.data_tab#overview
        self.pos = pos
        self.label = ['x','y']
        self.cut_index = self.sub_tab.data.get(type(self).__name__+'cut_index',0)
        self.init_data()
        self.original_int = self.int

        self.colour_limit()
        self.define_canvas(size = [4.45,4.3], top = 0.93, left = 0.15, right = 0.97, bottom = 0.11)
        self.define_export()
        self.define_mouse()
        self.draw()
        #self.define_normalise()

    def init_data(self):
        self.intensity()
        self.sort_data()

    def define_canvas(self, **kwarg):
        self.fig = plt.Figure(figsize = kwarg['size'])
        self.size = self.fig.get_size_inches()*self.fig.dpi
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(top = kwarg['top'],left = kwarg['left'],right = kwarg['right'], bottom = kwarg['bottom'])

        self.ax.set_yticklabels([])#to make the blank BG without any axis numbers
        self.ax.set_xticklabels([])
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        self.canvas = FigureCanvasTkAgg(self.fig, master = self.sub_tab.tab)
        self.canvas.draw()

        offset = [0,0]
        self.canvas.get_tk_widget().place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])#grid(row=1,column=self.column)
        self.blank_background = self.fig.canvas.copy_from_bbox(self.ax.get_figure().bbox)#including the axis
        self.canvas.get_tk_widget().bind( "<Button-2>", self.right_click)#right click
        self.canvas.get_tk_widget().bind( "<Double-Button-1>", self.double_click)#double click

    def mouse_range(self):#used for crusor
        self.xlimits = [np.nanmin(self.data[0]), np.nanmax(self.data[0])]
        self.ylimits = [np.nanmin(self.data[1]), np.nanmax(self.data[1])]

    def define_mouse(self):#called in init and from processing
        self.mouse_range()
        self.cursor = cursor.Auto_cursor(self)

        self.canvas.get_tk_widget().bind( "<Motion>", self.cursor.on_mouse_move)
        self.canvas.get_tk_widget().bind( "<Button-1>", self.cursor.on_mouse_click)#left click

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
            self.data[-1] = self.data[-1] + data['data']

        self.data[-1] = self.data[-1]/(len(files)+1)
        self.intensity()
        self.draw()

    def double_click(self,event):
        pass

    def click(self,pos):
        self.cursor.redraw()

    def right_click(self,event):
        self.sub_tab.data_tab.gui.pop_up(size = self.sub_tab.operations.fig_size_entry.get())#call gui to make a new window object
        self.plot(self.sub_tab.data_tab.gui.pop.ax)#plot the fraph onto the popup ax
        self.sub_tab.data_tab.gui.pop.graph = self.graph
        self.sub_tab.data_tab.gui.pop.set_vlim(self.vmin,self.vmax_set)
        self.sub_tab.data_tab.gui.pop.set_lim()
        self.sub_tab.data_tab.gui.pop.pop_canvas.draw()#draw it after plot
        self.plot(self.ax)#this is to re-updathe self.graph to the proper figure

    def draw(self):
        self.ax.cla()
        self.plot(self.ax)
        self.set_label()#shuoldn't be here perhaps?
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

    def update_colour_scale(self):#called from slider
        value = self.sub_tab.operations.color_scale.get()#value of the colour scale
        vmax = np.nanmax(self.vmax)*int(float(value))/100
        self.vmax_set = vmax#for the pop up window
        self.graph.set_clim(vmin = self.vmin, vmax = vmax)#all graphs have common have comon vmax and vmin
        self.sub_tab.operations.label3.configure(text=(float(value)))#update the number next to int range slide

    def colour_limit(self):#called in init and processing
        pass

class FS(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)
        self.figures = figure_handeler.figures
        self.tilt =  self.sub_tab.data['metadata']['tilt']
        self.define_add_data()#the botton to add data (e.g. several measurement but divided into several files)
        self.colour_bar = Colour_bar(self)

    def init_data(self):
        self.sort_data()
        self.intensity()

    def save(self):#to save the stuff: called when pressing the save botton thorugh the figure handlere
        self.sub_tab.data['xscale'] = self.data[0]
        self.sub_tab.data['yscale'] = self.data[1]
        self.sub_tab.data['zscale'] = self.data[2]
        self.sub_tab.data['data'] = self.data[3]

    def plot(self,ax):#pcolorfast
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap, norm = colors.Normalize(vmin = self.vmin, vmax = self.vmax))#FS

    def sort_data(self):
        self.data = [self.sub_tab.data['xscale'],self.sub_tab.data['yscale'],self.sub_tab.data['zscale'],self.sub_tab.data['data']]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0]-pos[0])
        self.figures['right'].cut_index = difference_array.argmin()

        self.figures['right'].intensity()
        self.figures['right'].plot(self.figures['right'].ax)
        self.figures['right'].redraw()
        self.figures['right'].click(pos)

        difference_array = np.absolute(self.data[1]-pos[1])
        self.figures['down'].cut_index = difference_array.argmin()

        self.figures['down'].intensity()
        self.figures['down'].plot(self.figures['down'].ax)
        self.figures['down'].redraw()
        self.figures['down'].click(pos)

    def intensity(self):
        start,stop,step = self.int_range(self.cut_index)
        self.int = np.nansum(self.data[3][start:stop:1],axis=0)/step#sum(self.data[3][start:stop:1])/step#this takes long tim for sum reason in kz space

    def define_hv(self):#called from procssing
        return self.data[1], np.array([self.tilt])

    def define_angle2k(self):#called from procssing, convert k
        return self.data[1], self.data[0]

    def update_colour_scale(self):
        super().update_colour_scale()
        self.colour_bar.update()

    def colour_limit(self):#called in init and processing
        self.vmin = np.nanmin(self.data[3])
        self.vmax = np.nanmax(self.data[3])

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
        new_data = {'xscale':self.data[0],'yscale':self.data[1],'zscale': None,'data':np.transpose(np.atleast_3d(self.int),axes=(2, 0, 1)),'metadata':self.sub_tab.data['metadata']}
        self.sub_tab.data_tab.append_tab(new_data)

    def plot(self,ax):
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band_right

    def intensity(self):
        start,stop,step = self.int_range(self.cut_index)
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
        self.figure_handeler.figures['corner'].cut_index = difference_array1.argmin()
        self.figure_handeler.figures['corner'].intensity_right()
        #self.figure_handeler.figures['corner'].draw()
        self.figure_handeler.figures['corner'].plot(self.figure_handeler.figures['corner'].ax)
        self.figure_handeler.figures['corner'].redraw()

    def colour_limit(self):#called in init and processing
        self.vmin = self.figure_handeler.figures['center'].vmin
        self.vmax = self.figure_handeler.figures['center'].vmax

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
        new_data = {'xscale':self.data[0],'yscale':self.data[1],'zscale': None,'data':np.transpose(np.atleast_3d(self.int),axes=(2, 0, 1)),'metadata':self.sub_tab.data['metadata']}
        self.sub_tab.data_tab.append_tab(new_data)

    def plot(self,ax):#2D plot
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int,zorder=1,cmap=self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band down

    def intensity(self):
        start,stop,step=self.int_range(self.cut_index)
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
        self.figure_handeler.figures['corner'].cut_index = difference_array1.argmin()

        self.figure_handeler.figures['corner'].intensity_down()
        #self.figure_handeler.figures['corner'].draw()
        self.figure_handeler.figures['corner'].plot(self.figure_handeler.figures['corner'].ax)
        self.figure_handeler.figures['corner'].redraw()

    def colour_limit(self):#called in init and processing
        self.vmin = self.figure_handeler.figures['center'].vmin
        self.vmax = self.figure_handeler.figures['center'].vmax

class DOS_right_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[2],self.int_right]

    def intensity(self):
        self.intensity_right()
        self.intensity_down()
        self.int = (self.int_right+self.int_down)*0.5
        self.colour_limit()

    def intensity_right(self):
        start,stop,step=self.int_range(self.cut_index)
        self.int_right = sum(self.figure_handeler.figures['right'].int[start:stop:1])/step

    def intensity_down(self):
        start,stop,step=self.int_range(self.cut_index)
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
        self.figure_handeler.figures['center'].cut_index = difference_array.argmin()
        self.figure_handeler.figures['center'].intensity()#this is slow for some reason in kz space
        self.figure_handeler.figures['center'].plot(self.figure_handeler.figures['center'].ax)
        self.figure_handeler.figures['center'].redraw()

    def update_colour_scale(self):
        pass

    def redraw(self):
        ymin=min(np.nanmin(self.int_right),np.nanmin(self.int_down))
        ymax=max(np.nanmax(self.int_right),np.nanmax(self.int_down))
        xmin=min(self.data[0])
        xmax=max(self.data[0])

        self.ax.set_xbound([xmin,xmax])
        self.ax.set_ybound([ymin,ymax])

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
        self.tilt = self.sub_tab.data['metadata']['tilt']
        self.figures = figure_handeler.figures
        self.define_add_data()
        self.colour_bar = Colour_bar(self)

    def init_data(self):
        self.sort_data()
        self.intensity()

    def plot(self,ax):#2D plot
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap, norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band
        #ax.set_ylim(74.7, 75.3)

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

    def save(self):#to save the stuff: called when pressing the save botton thorugh the figure handlere
        self.sub_tab.data['xscale'] = self.data[0]
        self.sub_tab.data['yscale'] = self.data[1]
        self.sub_tab.data['data'] = np.transpose(np.atleast_3d(self.int),(2, 0, 1))

    def sort_data(self):
        self.data = [self.sub_tab.data['xscale'], self.sub_tab.data['yscale'], self.sub_tab.data['data']]

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

    def update_colour_scale(self):
        super().update_colour_scale()
        self.colour_bar.update()

    def colour_limit(self):#called in init and processing
        self.vmin = np.nanmin(self.int)
        self.vmax = np.nanmax(self.int)

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

class Colour_bar(Figure):
    def __init__(self,figure):
        self.figure = figure
        self.sub_tab = figure.sub_tab#overview
        self.pos = [812,400]
        self.define_canvas(size = [7.64,1], top = 0.6, left = 0.1, right = 0.9, bottom = 0.4)
        self.bar = self.fig.colorbar(self.figure.graph,cax = self.ax,orientation='horizontal',label = 'Intensity')

    def update(self):
        self.bar.update_normal(self.figure.graph)
        self.bar.draw_all()
        self.canvas.draw()

    def right_click(self,event):#the popup window
        self.sub_tab.data_tab.gui.pop_up(size = self.figure.sub_tab.operations.colourbar_size_entry.get())#it returns a string)#call gui to make a new window object
        orientation = self.sub_tab.operations.orientation.configure('text')[-1]
        self.sub_tab.data_tab.gui.pop.fig.colorbar(self.figure.graph,cax = self.sub_tab.data_tab.gui.pop.ax,orientation=orientation,label = 'Intensity')
        #self.sub_tab.data_tab.gui.pop.fig.subplots_adjust(top = kwarg['top'],left = kwarg['left'],right = kwarg['right'], bottom = kwarg['bottom'])
        self.sub_tab.data_tab.gui.pop.set_lim()
        self.sub_tab.data_tab.gui.pop.pop_canvas.draw()#draw it after plot
