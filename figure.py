import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib import animation


import tkinter as tk
import numpy as np
import json
import sys

import processing, cursor, states_figure

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
        self.sort_data()
        self.intensity()
        self.original_int = self.int

        self.colour_limit()
        self.define_canvas()
        self.define_mouse()
        self.define_dropdowns()

        self.state = states_figure.Raw(self)
        self.data_processes = {'Raw':processing.Raw,'Derivative_x':processing.Derivative_x,'Derivative_y':processing.Derivative_y,'Convert_k':processing.Convert_k,'Range_plot':processing.Range_plot}
        self.set_method('Raw')
        #self.define_normalise()
        self.define_export()
        self.draw()

    def set_method(self,method):
        self.data_processor = self.data_processes[method](self)

    def define_canvas(self):
        self.fig = plt.Figure(figsize = [4.45,4.3])
        self.size = self.fig.get_size_inches()*self.fig.dpi
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(top=0.93,left=0.15,right=0.97)
        self.canvas = FigureCanvasTkAgg(self.fig, master = self.sub_tab.tab)
        self.canvas.draw()

        offset = [0,0]
        self.canvas.get_tk_widget().place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])#grid(row=1,column=self.column)

    def mouse_range(self):
        self.xlimits = [np.array(self.data[0]).min(), np.array(self.data[0]).max()]#used for crusor
        self.ylimits = [np.array(self.data[1]).min(), np.array(self.data[1]).max()]

    def define_mouse(self):#called in init and from processing
        self.mouse_range()
        self.cursor = cursor.Auto_cursor(self)

        self.canvas.get_tk_widget().bind( "<Motion>", self.cursor.on_mouse_move)
        self.canvas.get_tk_widget().bind( "<Button-1>", self.cursor.on_mouse_click)#left click
        self.canvas.get_tk_widget().bind( "<Button-2>", self.right_click)#right click
        self.canvas.get_tk_widget().bind( "<Double-Button-1>", self.double_click)#double click

    def define_dropdowns(self):
        commands = ['Raw','Derivative_x','Derivative_y','Convert_k']
        if str(type(self.sub_tab).__name__) == 'Analysis':#on analysis tab
            commands.append('Range_plot')

        dropvar = tk.StringVar()
        dropvar.set(commands[0])
        drop = tk.OptionMenu(self.sub_tab.tab,dropvar,*commands,command = self.select_drop)
        offset=[50,0]
        drop.place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])

    def select_drop(self,event):
        self.data_processor.exit()#exit the old one
        self.set_method(event)#point to new method and make the object
        self.data_processor.run()#run the thing
        self.draw()

    def double_click(self,event):
        pos = [self.sub_tab.center.pos[0],self.sub_tab.center.pos[1]]
        new_fig = type(self)#make a new figure
        self.sub_tab.data_tab.append_tab(new_fig,pos,self.int)

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
        self.canvas.restore_region(self.curr_background)
        self.ax.draw_artist(self.graph)
        self.canvas.blit(self.ax.bbox)
        self.curr_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def int_range(self,index):
        if self.sub_tab.int_range == 0:#if no integrate
            return index,index+1,1
        else:#if integrate
            if index-self.sub_tab.int_range < 0:
                index=self.sub_tab.int_range
            start = index-self.sub_tab.int_range
            stop = index+self.sub_tab.int_range+1
            step = stop - start
            return start,stop,step

    def define_export(self):
        button_calc = tk.Button(self.sub_tab.tab, text="Export", command = self.export)
        offset = [340,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def export(self):
        export_data = {'x':self.data[0].tolist(), 'y':self.data[1].tolist(), 'z':self.int.tolist()}
        path = self.sub_tab.data_tab.gui.start_path + '/' + self.sub_tab.data_tab.name
        with open(path+"_exported.json", "w") as outfile:
            json.dump(export_data, outfile)

    def set_label(self):#called from draw
        self.ax.set_xlabel(self.label[0])
        self.ax.set_ylabel(self.label[1])

    def colour_limit(self):#called in init
        self.vmin = self.int.min()
        self.vmax = self.int.max()

    def update_colour_scale(self,value):#called from figure handlere and slide
        self.vmax = self.int.max()*value
        self.graph.set_clim(vmin=self.vmin, vmax=self.vmax)
        #self.redraw()

    def gold(self):#sort the data: called from fermi_level processing init
        pass#self.data[0] is assumed to be kinetic energy need to transpose back and forth if this is not the case (not implemented)

class FS(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)
        self.label = ['x angle','y angle']
        self.figures = figure_handeler.figures
        #self.anim = animation.FuncAnimation(self.fig, self.animate)#,init_func = self.init_animation,blit=True)# init_func = self.init_animation,

    def animate(self,frame):#this probably runs every frame
        self.graph.set_array(self.int.ravel())
        self.curr_background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def plot(self,ax):#pcolorfast
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1,cmap=self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#FS
        #self.fig.colorbar(self.graph)

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.xscale,self.sub_tab.data_tab.data.yscale,self.sub_tab.data_tab.data.zscale,self.sub_tab.data_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0]-pos[0])
        index1 = difference_array.argmin()

        self.figures['right'].intensity(index1)
        self.figures['right'].tilt = self.data[0][index1]
        self.figures['right'].plot(self.figures['right'].ax)
        self.figures['right'].redraw()

        difference_array = self.state.difference_array(pos[1])
        index2 = difference_array.argmin()
        self.figures['down'].intensity(index2)
        self.figures['down'].tilt = self.data[1][index2]
        self.figures['down'].plot(self.figures['down'].ax)
        self.figures['down'].redraw()

    def intensity(self,z = 0):
        start,stop,step=self.int_range(z)
        self.int = sum(self.data[3][start:stop:1])/step

    def define_angle2k(self):#called from procssing
        return self.data[1], self.data[0]

    def angle2k(self,kx,ky):#the stuff to convert, called from k convert
        self.data[0] = kx
        self.data[1] = ky
        self.xlimits = [min(self.data[0][0]), max(self.data[0][0])]#used for crusor
        self.ylimits = [min(self.data[1][0]), max(self.data[1][-1])]

        self.figures['right'].data[1] = np.linspace(np.amin(ky),np.amax(ky),num=ky.shape[0])#make a 1D array from the 2D ky
        self.figures['down'].data[0] =np.linspace(np.amin(kx),np.amax(kx),num=kx.shape[1])#make a 1D array from the 2D kx

class Band_right(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def subtract_BG(self):#the BG botton calls it
        difference_array1 = np.absolute(self.data[0] - self.cursor.sta_vertical_line.get_data()[0])
        index1 = difference_array1.argmin()
        bg = np.mean(self.int[:,index1:len(self.data[0])],axis=1)#axis = 0is vertical, axis =1 is horizontal means
        int = self.int.transpose()
        int -=  bg
        self.int = int.transpose()
        self.draw()

    def plot(self,ax):
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band_right

    def intensity(self,y=0):
        start,stop,step = self.int_range(y)
        self.int = []
        for ary in self.figure_handeler.figures['center'].data[3]:
            self.int.append(np.sum(ary[:,start:stop:1],axis=1)/step)
        self.int = np.transpose(self.int)

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[2],self.figure_handeler.figures['center'].data[1],self.figure_handeler.figures['center'].data[3]]

    def click(self,pos):
        super().click(pos)
        difference_array1 = np.absolute(self.data[1]-pos[1])
        index1 = difference_array1.argmin()
        self.figure_handeler.figures['corner'].intensity_right(index1)
        self.figure_handeler.figures['corner'].draw()
        #self.gui.right_down.plot()
        #self.gui.right_down.redraw()

    def define_angle2k(self):#called from procssing
        return self.data[1],np.array([self.tilt])

    def angle2k(self,kx,ky):#the stuff to convert
        #self.data[0] = kx
        self.data[1] = ky
        self.ylimits = [min(self.data[1][0]), max(self.data[1][-1])]

class Band_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def subtract_BG(self):#the BG botton calls it
        difference_array1 = np.absolute(self.data[1] - self.cursor.sta_horizontal_line.get_data()[1])
        index1 = difference_array1.argmin()
        bg = np.mean(self.int[index1:len(self.data[1]),:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
        self.int -=  bg
        self.draw()

    def plot(self,ax):#2D plot
        self.graph = ax.pcolorfast(self.data[0], self.data[1], self.int,zorder=1,cmap=self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#FS

    def intensity(self,y=0):
        start,stop,step=self.int_range(y)
        int = []
        for ary in self.figure_handeler.figures['center'].data[3]:
            int.append(sum(ary[start:stop:1])/step)
        self.int = np.array(int)

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[0], self.figure_handeler.figures['center'].data[2],self.figure_handeler.figures['center'].data[3]]

    def click(self,pos):
        super().click(pos)
        difference_array1 = np.absolute(self.data[0]-pos[0])
        index1 = difference_array1.argmin()

        self.figure_handeler.figures['corner'].intensity_down(index1)
        self.figure_handeler.figures['corner'].draw()
        #self.gui.right_down.plot()
        #self.gui.right_down.redraw()

    def angle2k(self,kx,ky):#the stuff to convert
        self.data[0] = kx
        #self.data[1] = ky
        self.xlimits = [min(self.data[0][0]), max(self.data[0][0])]#used for crusor

    def define_angle2k(self):#called from procssing
        return np.array([self.tilt]),self.data[0]

class DOS_right_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        self.data = [self.figure_handeler.figures['center'].data[2],self.figure_handeler.figures['center'].data[2]]

    def intensity(self,idx=0):
        self.intensity_right(idx)
        self.intensity_down(idx)
        self.int = (self.int_right+self.int_down)*0.5

    def intensity_right(self,idx=0):
        start,stop,step=self.int_range(idx)
        self.int_right = sum(self.figure_handeler.figures['right'].int[start:stop:1])/step

    def intensity_down(self,idx=0):
        start,stop,step=self.int_range(idx)
        self.int_down=[]
        for ary in self.figure_handeler.figures['down'].int:
            self.int_down.append(sum(ary[start:stop:1])/step)

    def plot(self,ax):#2D plot
        self.graph1 = ax.plot(self.data[0], self.int_right,zorder=3)[0]
        self.graph2 = ax.plot(self.data[0], self.int_down,zorder=3)[0]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.figure_handeler.figures['center'].data[2]-pos[0])
        index1 = difference_array.argmin()
        self.figure_handeler.figures['center'].intensity(index1)
        self.figure_handeler.figures['center'].plot(self.figure_handeler.figures['center'].ax)
        self.figure_handeler.figures['center'].redraw()

    def update_colour_scale(self,value):
        pass

    def redraw(self):
        pass

class Band(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)
        self.tilt = -3.5#np.array([float(self.sub_tab.data_tab.data.metadata['T'])])
        self.figures = figure_handeler.figures

    def subtract_BG(self):#the BG botton calls it
        self.state.bg_subtract()#run the appropriate method
        self.draw()
        self.click([self.cursor.sta_vertical_line.get_data()[0],self.cursor.sta_horizontal_line.get_data()[1]])#update the right and down figures

    def plot(self,ax):#2D plot
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax))#band
        #ax.set_ylim(74.7, 75.3)

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.xscale, self.sub_tab.data_tab.data.yscale, self.sub_tab.data_tab.data.data]

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
        self.int = self.sub_tab.data_tab.data.data[0]

    def angle2k(self,kx,ky):#the stuff to convert
        self.data[1] = ky.ravel()
        self.ylimits = [min(self.data[1]), max(self.data[1])]

    def define_angle2k(self):#called from procssing
        return self.data[1],np.array([self.tilt])

class DOS_right(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        self.intensity()
        self.data = [self.int,self.figure_handeler.figures['center'].data[1]]

    def intensity(self,x = 0):
        start,stop,step=self.int_range(x)
        int = []
        for ary in self.figure_handeler.figures['center'].int:
            int.append(sum(ary[start:stop:1])/step)
        self.int = np.array(int)

    def plot(self,ax):#2D plot
        self.graph = ax.plot(self.int,self.figure_handeler.figures['center'].data[1])[0]#DOS right

    def update_colour_scale(self):
        pass

class DOS_down(Figure):
    def __init__(self,figure_handeler,pos):
        super().__init__(figure_handeler,pos)

    def sort_data(self):
        self.intensity()
        self.data = [self.figure_handeler.figures['center'].data[0],self.int]

    def intensity(self,y=0):
        start,stop,step=self.int_range(y)
        self.int = sum(self.figure_handeler.figures['center'].int[start:stop:1])/step
        #self.int = self.sub_tab.center.int[y]

    def plot(self,ax):#2D plot
        self.graph = ax.plot(self.figure_handeler.figures['center'].data[0], self.int)[0]#DOS down

    def update_colour_scale(self):
        pass

class Band_scan(Figure):
    def __init__(self,data_tab,pos):
        super().__init__(data_tab,pos)
        self.define_slide()
        self.right = DOS_right(self,[self.pos[0]+self.size[0],self.pos[1]])
        self.down = DOS_down(self,[self.pos[0],self.pos[1]+self.size[1]])

    def define_slide(self):
        scale = tk.Scale(self.sub_tab.tab,from_=0,to=len(self.sub_tab.data_tab.data.data[0][0][0])-1,orient=tk.HORIZONTAL,label='scan number',command=self.update_range,resolution=1)
        scale.pack()

    def update_range(self,value):
        self.intensity(int(value))
        self.draw()

    def plot(self,ax=None):#2D plot
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int,zorder=1,cmap=self.sub_tab.cmap)#FS

    def intensity(self,y = 0):
        #self.int = self.sub_tab.data_tab.data.data[0]
        inss = []
        for int in self.sub_tab.data_tab.data.data[0]:
            for ins in int:
                inss.append(ins[y])

        self.int = np.array(inss).reshape((len(self.sub_tab.data_tab.data.data[0][0]),len(self.sub_tab.data_tab.data.data[0])),order='F')

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.yscale, self.sub_tab.data_tab.data.xscale, self.sub_tab.data_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.sub_tab.data_tab.data.xscale-pos[0])
        index1 = difference_array.argmin()
        self.right.intensity(index1)
        self.right.draw()
        #self.right.plot()
        #self.right.redraw()

        difference_array = np.absolute(self.sub_tab.data_tab.data.yscale-pos[1])
        index2 = difference_array.argmin()
        self.down.intensity(index2)
        self.down.draw()
        #self.down.plot()
        #self.down.redraw()

    def draw(self):
        super().draw()
        self.right.draw()
        self.down.draw()
