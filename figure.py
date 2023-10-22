import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)

import tkinter as tk
import numpy as np
import json#for the export

import processing, cursor, data_loader, constants

class Functions():#figure functionality not being used
    def __init__(self):
        pass

    def subtract_BG(self):#the BG botton calls it
        pass

    def make_grid(self,ax):#called when pressing the botton, from figure handlere
        ax.grid(self.grid)#self.grid toggles when pressing the botton
        self.canvas.draw()#would like to blit it instead somehow
        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)

class Figure(Functions):
    def __init__(self,figure_handeler,pos):
        self.figure_handeler = figure_handeler
        self.overview = figure_handeler.overview#overview
        self.pos = pos
        self.label = ['x','y']
        self.grid = False#plot with grid
        self.cut_index = self.overview.data_handler.files[0].save_dict.get(type(self).__name__+'cut_index',0)
        self.init_data()

        self.define_canvas(size = constants.figure_size['size'], top = constants.figure_size['top'], left = constants.figure_size['left'], right = constants.figure_size['right'], bottom = constants.figure_size['bottom'])
        self.define_export()
        self.define_mouse()
        self.draw()

    def init_data(self):
        self.intensity()
        self.sort_data()

    def define_canvas(self, **kwarg):
        self.fig = plt.Figure(figsize = kwarg['size'])
        self.size = self.fig.get_size_inches()*self.fig.dpi
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(top = kwarg['top'], left = kwarg['left'], right = kwarg['right'], bottom = kwarg['bottom'])

        self.ax.set_yticklabels([])#to make the blank BG without any axis numbers
        self.ax.set_xticklabels([])
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        self.canvas = FigureCanvasTkAgg(self.fig, master = self.overview.tab)
        self.canvas.draw()

        offset = [0,0]
        self.canvas.get_tk_widget().place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])#grid(row=1,column=self.column)
        self.blank_background = self.fig.canvas.copy_from_bbox(self.ax.get_figure().bbox)#including the axis
        self.canvas.get_tk_widget().bind( "<Button-2>", self.right_click)#right click
        self.canvas.get_tk_widget().bind( "<Double-Button-1>", self.double_click)#double click

        self.menue = tk.Menu(self.overview.tab, tearoff = 0)
        self.menue.add_command(label = "new", command = lambda: self.pop_up(self.overview.data_tab))
        self.menue.add_command(label = "add", command = lambda: self.pop_up(self.overview.data_tab.gui))

    def mouse_range(self):#used for crusor
        self.xlimits = [np.nanmin(self.data[0]), np.nanmax(self.data[0])]
        self.ylimits = [np.nanmin(self.data[1]), np.nanmax(self.data[1])]

    def define_mouse(self):#called in init and from processing
        self.mouse_range()
        self.cursor = cursor.Auto_cursor(self)

        self.canvas.get_tk_widget().bind( "<Motion>", self.cursor.on_mouse_move)
        self.canvas.get_tk_widget().bind( "<Button-1>", self.cursor.on_mouse_click)#left click
        self.canvas.get_tk_widget().bind( "<B1-Motion>", self.cursor.on_mouse_click)#left click

    def define_export(self):
        button_calc = tk.ttk.Button(self.overview.tab, text="Export", command = self.export)
        offset = [320,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def export(self):
        export_data = {'x':self.data[0].tolist(), 'y':self.data[1].tolist(), 'z':self.int.tolist()}
        path = self.overview.data_tab.gui.start_path + '/' + self.overview.data_tab.name
        with open(path+"_exported.json", "w") as outfile:
            json.dump(export_data, outfile)

    def double_click(self,event):
        pass

    def click(self,pos):
        self.cursor.redraw()

    def right_click(self,event):
        try:
            self.menue.tk_popup(event.x_root, event.y_root)
        finally:#called when selecting
            self.menue.grab_release()

    def pop_up(self,target):
        target.pop_up(size = self.overview.operations.fig_size_entry.get(),top = self.overview.operations.fig_margines['top'].get(),left = self.overview.operations.fig_margines['left'].get(),right = self.overview.operations.fig_margines['right'].get(),bottom = self.overview.operations.fig_margines['bottom'].get())#call gui to make a new window object
        self.plot(target.pop[-1].ax)#plot the fraph onto the popup ax
        self.make_grid(target.pop[-1].ax)
        target.pop[-1].graph = self.graph#corner doesn't have it
        target.pop[-1].set_lim()
        target.pop[-1].canvas.draw()#draw it after plot
        self.plot(self.ax)#this is to re-updathe self.graph to the proper figure

    def draw(self):
        self.ax.cla()
        self.plot(self.ax)
        self.set_label()#shuoldn't be here perhaps?
        self.canvas.draw()
        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def redraw(self):
        self.canvas.restore_region(self.blank_background)
        self.ax.draw_artist(self.graph)
        #self.make_grid(self.ax) -> a little slow
        self.canvas.blit(self.ax.bbox)
        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def int_range(self,index):
        if self.figure_handeler.int_range == 0:#if no integrate
            return index, index + 1, 1
        else:#if integrate
            if index-self.figure_handeler.int_range < 0:
                index = self.figure_handeler.int_range
            start = index - self.figure_handeler.int_range
            stop = index + self.figure_handeler.int_range + 1
            step = stop - start
            return start, stop, step

    def set_label(self):#called from draw
        self.ax.set_xlabel(self.label[0])
        self.ax.set_ylabel(self.label[1])

    def update_colour_scale(self):#called from figure handlere
        self.graph.set_clim(vmin = self.figure_handeler.colour_bar.vlim_set[0], vmax = self.figure_handeler.colour_bar.vlim_set[1])#all graphs have common have comon vmax and vmin

class FS(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)
        self.figures = figure_handeler.figures
        self.tilt = self.overview.data_handler.file.get_data('metadata')['tilt']

    def subtract_BG(self):#move to processing? #the BG botton calls it from figure handlre
        dict = self.overview.data_handler.file.data[-1].copy()
        if self.overview.operations.BG_orientation.configure('text')[-1] == 'vertical':#vertical bg subtract
            pass
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'horizontal':#horizontal bg subtract
            difference_array1 = np.absolute(self.figure_handeler.figures['right'].data[0] - self.figure_handeler.figures['right'].cursor.sta_vertical_line.get_data()[0])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.data[3][index1:-1:,:],axis=0)
            new_int = self.data[3] - bg
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'EDC':#EDC bg subtract
            pass
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'bg Matt':#EDC bg subtract
            pass

        dict['data'] = new_int
        self.overview.data_handler.file.add_state(dict,'bg_subtract')
        self.overview.data_handler.append_state('bg_subtract', len(self.overview.data_handler.file.states))
        self.overview.data_handler.update_catalog()
        self.figure_handeler.new_stack()

        self.click([self.cursor.sta_vertical_line.get_data()[0],self.cursor.sta_horizontal_line.get_data()[1]])#update the right and down figures

    def init_data(self):#called in init
        self.sort_data()
        self.intensity()

    def save(self):#to save the stuff: called when pressing the save botton thorugh the figure handlere
        self.overview.data_handler.file.set_data('xscale',self.data[0])
        self.overview.data_handler.file.set_data('yscale',self.data[1])
        self.overview.data_handler.file.set_data('zscale',self.data[2])
        self.overview.data_handler.file.set_data('data',self.data[3])

    def plot(self,ax):#pcolorfast
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int, zorder=1, cmap = self.figure_handeler.cmap)#, norm = colors.Normalize(vmin = self.overview.vlim_set[0], vmax = self.overview.vlim_set[1]))#FS

    def sort_data(self):
        self.data = [self.overview.data_handler.file.get_data('xscale'),self.overview.data_handler.file.get_data('yscale'),self.overview.data_handler.file.get_data('zscale'),self.overview.data_handler.file.get_data('data')]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0]-pos[0])
        self.figures['right'].cut_index = difference_array.argmin()
        self.figures['right'].intensity()
        self.figures['right'].graph.set_array(self.figures['right'].int)
        self.figures['right'].redraw()
        self.figures['right'].click(pos)

        difference_array = np.absolute(self.data[1]-pos[1])
        self.figures['down'].cut_index = difference_array.argmin()
        self.figures['down'].intensity()
        self.figures['down'].graph.set_array(self.figures['down'].int)
        self.figures['down'].redraw()
        self.figures['down'].click(pos)

    def intensity(self):
        start,stop,step = self.int_range(self.cut_index)
        self.int = np.nansum(self.data[3][start:stop:1],axis=0)/step#sum(self.data[3][start:stop:1])/step#this takes long tim for sum reason in kz space

    def define_hv(self):#called from procssing
        return self.data[1], np.array([self.tilt])

    def define_angle2k(self):#called from procssing, convert k
        return self.data[1], self.data[0]

    def popup(self,target):
        super().pop_up(target)
        target.pop.set_vlim(self.figure_handeler.colour_bar.vlim_set[0],self.figure_handeler.colour_bar.vlim_set[1])#2D doens't have vlim

class Band_right(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def double_click(self,event):#called when doubleclicking
        new_data = {'xscale':self.data[0],'yscale':self.data[1],'zscale': None,'data':np.transpose(np.atleast_3d(self.int),axes=(2, 0, 1)),'metadata':self.overview.data_handler.file['metadata']}
        self.overview.data_tab.append_tab(new_data)

    def plot(self,ax):
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int, zorder=1, cmap = self.figure_handeler.cmap)#, norm = colors.Normalize(vmin = self.overview.vlim_set[0], vmax = self.overview.vlim_set[1]))#band_right

    def intensity(self):
        start,stop,step = self.int_range(self.cut_index)
        temp = np.transpose(self.figure_handeler.figures['center'].data[3])
        self.int = np.sum(temp[start:stop:1,:,:],axis=0)/step

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[2],self.figure_handeler.figures['center'].data[1],self.figure_handeler.figures['center'].data[3]]

    def click(self,pos):
        super().click(pos)
        pos = self.cursor.sta_horizontal_line.get_data()#needed to redraw when clicking on FS

        difference_array1 = np.absolute(self.data[1]-pos[1])
        self.figure_handeler.figures['corner'].cut_index = difference_array1.argmin()
        self.figure_handeler.figures['corner'].intensity_right()
        self.figure_handeler.figures['corner'].graph1.set_ydata(self.figure_handeler.figures['corner'].int_right)
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
        new_data = {'xscale':self.data[0],'yscale':self.data[1],'zscale': None,'data':np.transpose(np.atleast_3d(self.int),axes=(2, 0, 1)),'metadata':self.overview.data['metadata']}
        self.overview.data_tab.append_tab(new_data)

    def plot(self,ax):#2D plot
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int,zorder=1,cmap=self.figure_handeler.cmap)#, norm = colors.Normalize(vmin = self.overview.vlim_set[0], vmax = self.overview.vlim_set[1]))#band down

    def intensity(self):
        start,stop,step=self.int_range(self.cut_index)
        self.int = np.sum(self.figure_handeler.figures['center'].data[3][:,start:stop:1,:],axis=1)/step

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[0], self.figure_handeler.figures['center'].data[2],self.figure_handeler.figures['center'].data[3]]

    def click(self,pos):
        super().click(pos)
        pos = self.cursor.sta_vertical_line.get_data()#needed to redraw when clicking on FS
        difference_array1 = np.absolute(self.data[0]-pos[0])
        self.figure_handeler.figures['corner'].cut_index = difference_array1.argmin()
        self.figure_handeler.figures['corner'].intensity_down()
        self.figure_handeler.figures['corner'].graph2.set_ydata(self.figure_handeler.figures['corner'].int_down)
        self.figure_handeler.figures['corner'].redraw()

class DOS_right_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[2],self.int_right]

    def intensity(self):
        self.intensity_right()
        self.intensity_down()
        self.int = (self.int_right+self.int_down)*0.5

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
        self.figure_handeler.figures['center'].graph.set_array(self.figure_handeler.figures['center'].int)
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
        self.tilt = self.overview.data_handler.file.get_data('metadata')['tilt']
        self.figures = figure_handeler.figures

    def init_data(self):#called in init
        self.sort_data()
        self.intensity()

    def plot(self,ax):#2D plot
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1, cmap = self.figure_handeler.cmap)#, norm = colors.Normalize(vmin = self.overview.vlim_set[0], vmax = self.overview.vlim_set[1]))#band

    def subtract_BG(self):#move to processing? #the BG botton calls it from figure handlre
        dict = self.overview.data_handler.file.data[-1].copy()
        if self.overview.operations.BG_orientation.configure('text')[-1] == 'vertical':#vertical bg subtract
            difference_array1 = np.absolute(self.data[1] - self.cursor.sta_horizontal_line.get_data()[1])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.int[index1:-1,:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
            new_int = self.int - bg
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'horizontal':#horizontal bg subtract
            difference_array1 = np.absolute(self.data[0] - self.cursor.sta_vertical_line.get_data()[0])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.int[:,index1:-1],axis=1)#axis = 0is vertical, axis =1 is horizontal means
            int = np.transpose(self.int) - bg
            new_int = np.transpose(int)
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'EDC':#EDC bg subtract
            new_int = self.int - self.figures['down'].int[None,:]#subtract the EDC from each row in data
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'bg Matt':#EDC bg subtract
            new_int = self.int.copy()
            for index, ary in enumerate(np.transpose(self.int[200:600,:])):#MDCs -> deifine the area...
                new_int[:,index] -= np.nanmin(ary)
                #plt.plot(ary)
                #plt.show()
        dict['data'] = np.transpose(np.atleast_3d(new_int),(2,0,1))
        self.overview.data_handler.file.add_state(dict,'bg_subtract')
        self.overview.data_handler.append_state('bg_subtract', len(self.overview.data_handler.file.states))
        self.overview.data_handler.update_catalog()
        self.figure_handeler.new_stack()
        self.click([self.cursor.sta_vertical_line.get_data()[0],self.cursor.sta_horizontal_line.get_data()[1]])#update the right and down figures

    def save(self):#to save the stuff: called when pressing the save botton thorugh the figure handlere
        self.overview.data_handler.file.set_data('xscale',self.data[0])
        self.overview.data_handler.file.set_data('yscale',self.data[1])
        self.overview.data_handler.file.set_data('data',np.transpose(np.atleast_3d(self.int),(2, 0, 1)))

    def sort_data(self):
        self.data = [self.overview.data_handler.file.get_data('xscale'), self.overview.data_handler.file.get_data('yscale'), self.overview.data_handler.file.get_data('data')]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0] - pos[0])#subtract for each channel, works.
        self.figures['right'].cut_index = np.argmin(difference_array)
        self.figures['right'].intensity()
        self.figures['right'].redraw()

        difference_array = np.absolute(self.data[1] - pos[1])
        self.figures['down'].cut_index = np.argmin(difference_array)
        self.figures['down'].intensity()
        self.figures['down'].redraw()

    def intensity(self,y = 0):
        self.int = self.data[-1][0]

    def define_angle2k(self):#called from procssing
        return self.data[1],np.array([self.tilt])

class DOS_right(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        self.data = [self.int,self.figure_handeler.figures['center'].data[1]]

    def integrate(self):#EDC: called from figure hadnlre
        self.int = np.sum(self.figure_handeler.figures['center'].int,axis=1)/len(self.figure_handeler.figures['center'].int[0,:])

    def intensity(self):
        start,stop,step = self.int_range(self.cut_index)
        temp = np.transpose(self.figure_handeler.figures['center'].int)
        self.int = np.sum(temp[start:stop:1],axis=0)/step
        self.sort_data()

    def plot(self,ax):#2D plot
        self.graph = ax.plot(self.int,self.figure_handeler.figures['center'].data[1])[0]#DOS right

    def redraw(self):
        self.graph.set_xdata(self.int)
        xmin = np.nanmin(self.int)
        xmax = np.nanmax(self.int)
        ymin=min(self.data[1])
        ymax=max(self.data[1])

        self.ax.set_xbound([xmin,xmax])
        self.ax.set_ybound([ymin,ymax])

        self.canvas.restore_region(self.blank_background)
        self.ax.draw_artist(self.ax.get_yaxis())
        self.ax.draw_artist(self.ax.get_xaxis())

        self.ax.draw_artist(self.graph)

        self.canvas.blit(self.ax.clipbox)

        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

class DOS_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def integrate(self):#MDC: called from figure hadnlre
        self.int = np.nansum(self.figure_handeler.figures['center'].int,axis=0)/len(self.figure_handeler.figures['center'].int)

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[0],self.int]

    def intensity(self):
        start,stop,step=self.int_range(self.cut_index)
        self.int = sum(self.figure_handeler.figures['center'].int[start:stop:1])/step
        self.sort_data()

    def plot(self,ax):#2D plot
        self.graph = ax.plot(self.figure_handeler.figures['center'].data[0], self.int)[0]#DOS down

    def redraw(self):
        self.graph.set_ydata(self.int)
        ymin=np.nanmin(self.int)
        ymax=np.nanmax(self.int)
        xmin=min(self.data[0])
        xmax=max(self.data[0])

        self.ax.set_xbound([xmin,xmax])
        self.ax.set_ybound([ymin,ymax])

        self.canvas.restore_region(self.blank_background)
        self.ax.draw_artist(self.ax.get_yaxis())
        self.ax.draw_artist(self.ax.get_xaxis())

        self.ax.draw_artist(self.graph)

        self.canvas.blit(self.ax.clipbox)

        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

class Colour_bar(Figure):
    def __init__(self,figure_handler):
        self.figure_handler = figure_handler
        self.overview = figure_handler.overview#overview
        self.pos = constants.colourbar_position
        self.define_canvas(size = constants.colourbar_size['size'], top = constants.colourbar_size['top'], left = constants.colourbar_size['left'], right = constants.colourbar_size['right'], bottom = constants.colourbar_size['bottom'])
        self.bar = self.fig.colorbar(self.figure_handler.figures['center'].graph,cax = self.ax,orientation='horizontal',label = 'Intensity')

        self.vlim = [np.nanmin(self.figure_handler.figures['center'].int),np.nanmax(self.figure_handler.figures['center'].int)]#set common vlim
        self.vlim_set = self.vlim.copy()#save original one seperately

    def update(self):#called from figure handlere
        self.bar.update_normal(self.figure_handler.figures['center'].graph)
        self.bar.draw_all()
        self.canvas.draw()

    def pop_up(self,target):#the popup window
        self.overview.data_tab.gui.pop_up(size = self.overview.operations.colourbar_size_entry.get(),top = self.overview.operations.colourbar_margines['top'].get(),left = self.overview.operations.colourbar_margines['left'].get(),right = self.overview.operations.colourbar_margines['right'].get(),bottom = self.overview.operations.colourbar_margines['bottom'].get())#call gui to make a new window object
        orientation = self.overview.operations.colourbar_orientation.configure('text')[-1]
        self.overview.data_tab.gui.pop[0].fig.colorbar(self.figure_handler.figures['center'].graph,cax = self.overview.data_tab.gui.pop[0].ax,orientation=orientation,label = 'Intensity')
        #self.overview.data_tab.gui.pop.fig.subplots_adjust(top = kwarg['top'],left = kwarg['left'],right = kwarg['right'], bottom = kwarg['bottom'])
        self.overview.data_tab.gui.pop[0].set_lim()
        self.overview.data_tab.gui.pop[0].canvas.draw()#draw it after plot

    def set_vlim(self):#called from botton
        values = self.overview.operations.vlim_entry.get()
        value = values.split(',')

        if value[0] != 'None':
            self.vlim_set[0] = float(value[0])
        else:
            self.vlim_set[0] = np.nanmin(self.figure_handler.figures['center'].int)
        if value[1] != 'None':
            self.vlim_set[1] = float(value[1])
        else:
            self.vlim_set[1] = np.nanmax(self.figure_handler.figures['center'].int)

        self.vlim = self.vlim_set.copy()#update to new reference
        for figure in self.figure_handler.twoD:#update the figures
            self.figure_handler.figures[figure].update_colour_scale()
        self.update()#update the colourbar
        self.figure_handler.redraw()
