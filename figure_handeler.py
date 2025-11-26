import figure, processing, constants, data_handler
import numpy as np
import copy
#import matplotlib.pyplot as plt

class Figure_handeler():
    def __init__(self,overview):
        self.overview = overview#overview
        self.pos = constants.figure_position#posirion of the main figure
        self.size = constants.figure_grid#figure canvas size
        self.int_range = self.overview.data_handler.save_dict.get('int_range',0)#should be moved to operations?
        self.cmap = self.overview.data_handler.save_dict.get('cmap','RdYlBu_r')#should be moved to operations?
        self.make_figures()
        self.colour_bar = figure.Colour_bar(self)

    def new_stack(self):#called when a new stack is attached and when selecting a new stack
        self.update_sort_data()
        self.update_intensity()
        self.draw()
        self.colour_bar.set_vlim()
        self.update_mouse_range()

    def update_intensity(self):#called after k convert or fermi adjust
        for figure in self.figures.values():
            figure.intensity()

    def update_sort_data(self):#called after k convert or fermi adjust
        for figure in self.figures.values():
            figure.sort_data()

    def update_mouse_range(self):#called after k convert or fermi adjust
        for figure in self.figures.values():
            figure.mouse_range()#update the x,y limits

    def update_line_width(self):
        for figure in self.figures.values():
            figure.cursor.update_line_width()

    def draw(self):
        for figure in self.figures.values():
            figure.draw()

    def redraw(self,*arg):#called from overview (init), colour scale slide,
        for figure in self.figures.values():
            figure.redraw()

    #methods
    def k_convert(self):#called when pressed the botton
        adjust = processing.Convert_k(self.figures['center'])
        adjust.run()

    def derivative(self):#called when pushing the 2nd derivative botton
        if self.overview.operations.orientation_botton.configure('text')[-1] == 'horizontal':
            adjust = processing.Derivative_x(self.figures['center'])
        else:#vertical
            adjust = processing.Derivative_y(self.figures['center'])
        adjust.run()
        self.draw()

    def curvature(self):#called when pushing the 2nd derivative botton
        if self.overview.operations.orientation_botton.configure('text')[-1] == 'horizontal':
            adjust = processing.Curvature_x(self.figures['center'])
        else:#vertical
            adjust = processing.Curvature_y(self.figures['center'])
        adjust.run()
        self.draw()

    def smooth(self):#the smooth botton
        adjust = processing.Smooth(self.figures['center'],self.overview.operations.orientation_botton.configure('text')[-1])
        adjust.run()
        self.draw()

    def save(self):
        self.figures['center'].save()

    def update_colour_scale(self,value = 0):#called from slider
        value = self.overview.operations.color_scale.get()#value of the colour scale
        vmax = self.colour_bar.vlim[1]*float(value)/100
        self.colour_bar.vlim_set = [self.colour_bar.vlim[0],vmax]#for the pop up window -> should just be called once
        self.overview.operations.label3.configure(text = (round(float(value),1)))#update the number next to int range slide -> should just be called once

        for figure in self.twoD:#update the 2D figures
            self.figures[figure].update_colour_scale()
        self.colour_bar.update()
        self.redraw()

    def make_grid(self):#called from botton
        for figure in self.figures.values():
            figure.make_grid(figure.ax)

    def make_hori_clip(self):#clips the data based on 2 horizontal lines
        values = []
        dict = copy.deepcopy(self.overview.data_handler.file.data[self.overview.data_handler.file.index])
        for entry in self.overview.operations.hori_clip_enties:
            values.append(float(entry.get()))
        min_index = np.argmin(np.abs(self.figures['center'].data[1]-min(values)))
        max_index = np.argmin(np.abs(self.figures['center'].data[1]-max(values)))

        dict['data'] = dict['data'][:,min_index:max_index,:]
        dict['yscale'] = dict['yscale'][min_index:max_index]

        self.overview.data_handler.state_catalog.add_state(dict,'clipped'+str(min(values))+','+str(min(values)))

class Threedimension(Figure_handeler):#fermi surface
    def __init__(self,overview):
        super().__init__(overview)
        self.twoD = ['center','right','down']

    def make_figures(self):
        figures = {'center':figure.FS,'right':figure.Band_right,'down':figure.Band_down,'corner':figure.DOS_right_down}
        positions = {'center':[self.pos[0],self.pos[1]],'right':[self.pos[0]+self.size[0],self.pos[1]],'down':[self.pos[0],self.pos[1]+self.size[1]],'corner':[self.pos[0]+self.size[0],self.pos[1]+self.size[1]]}
        self.figures = {}
        for key in figures.keys():
            self.figures[key] = figures[key](self, positions[key])#figures are initated here

    def fermi_level(self):#corrects the fermi level based on a referecnce (gold) cut
        adjust = processing.Fermi_level_FS(self.figures['center'])
        adjust.run()

    def kz_convert(self):#called when pressed the botton
        adjust = processing.Convert_kz(self.figures['center'])
        adjust.run()

    def normalise_slices(self):#normalise each slice in a 3D data. useful for e.g. for kz
        temp = np.transpose(self.figures['center'].data[3],(2, 0, 1))
        temp2 = self.figures['center'].data[3].copy()
        for index, ary in enumerate(temp):#divide each angle with maximum
            temp2[:,:,index] =  100000000*len(ary)*ary/np.sum(ary)#need to multiply woth large number to compensate for the fact that it becomes int, and not float

        dict = self.overview.data_handler.file.data[-1].copy()
        dict['data'] = temp2
        self.overview.data_handler.state_catalog.add_state(dict,'normalise')

    def integrate(self):#sums up the EDC
        self.figures['corner'].int_right = np.nansum(self.figures['right'].int,axis=0)/len(self.figures['right'].int)
        self.figures['corner'].int_down = np.nansum(self.figures['down'].int,axis=1)/len(self.figures['down'].int[0,:])

        self.figures['corner'].artists['graph2'].set_ydata(self.figures['corner'].int_down)
        self.figures['corner'].artists['graph1'].set_ydata(self.figures['corner'].int_right)
        self.redraw()

    def EF_corr(self):#corrects EF based on oneself
        adjust = processing.EF_corr_3D(self.figures['center'])
        adjust.run()

    def make_circle(self):#makes a circle that defines the region of inetres. Works for EF corr now
        self.figures['center'].make_circle()

    def normalise_by(self):#-2D data: it normalises the center figure by what is plotted in teh EDC or MDC
        pass

    def normalise_cuts(self):#notmalises the cuts to 1
        self.figures['corner'].int_down =  self.figures['corner'].int_down/np.nanmax(self.figures['corner'].int_down)
        self.figures['corner'].int_right =  self.figures['corner'].int_right/np.nanmax(self.figures['corner'].int_right)
        self.redraw()

    def symmetrise(self):#called when pressed the botton
        pass

    def divide_by(self):
        dict = copy.deepcopy(self.overview.data_handler.file.data[self.overview.data_handler.file.index])
        if self.overview.operations.divide_by.configure('text')[-1] == '...':#reads in a ile and divide the center figure with this file
            ref_data, gold = self.overview.data_tab.data_loader.gold_please()
            if not ref_data: return#if press cancel

            if ref_data[0]['data'].shape[0] == 1:#2D data, divide a 2D spectra on all deflector angles
                temp = ref_data[0]['data'][0]#replace 0 with nan
                temp = temp.astype('float')
                temp[temp == 0] = np.nan

                result = np.transpose(self.figures['center'].data[-1],(1,2,0))/temp[:, np.newaxis]
                dict['data'] = np.transpose(result,(2,0,1))
            else:#3D data, divide each slice with each slice
                temp = ref_data[0]['data']#replace 0 with nan
                temp = temp.astype('float')
                temp[temp == 0] = np.nan

                result = self.figures['center'].data[-1]/temp
                dict['data'] = result
            name = gold[gold.rfind('/')+1:]

        elif self.overview.operations.divide_by.configure('text')[-1] == 'MDC':
            pass
        elif self.overview.operations.divide_by.configure('text')[-1] == 'EDC':#EDC
            pass

        self.overview.data_handler.state_catalog.add_state(dict,'divided_by:_'+name)

    def subtract_by(self):
        dict = self.overview.data_handler.file.data[-1].copy()
        if self.overview.operations.BG_orientation.configure('text')[-1] == '...':#reads in a ile and divide the center figure with this file
            ref_data, gold = self.overview.data_tab.data_loader.gold_please()
            if not ref_data: return#if press cancel

            if ref_data[0]['data'].shape[0] == 1:#2D data, subtract a 2D spectra on all deflector angles
                result = np.transpose(self.figures['center'].data[-1],(1,2,0)) - ref_data[0]['data'][0][:, np.newaxis]
                new_int = np.transpose(result,(2,0,1))
            else:#3D data, subtarct each slice with each slice
                new_int = self.figures['center'].data[-1] - ref_data[0]['data']
            name = gold[gold.rfind('/')+1:]

        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'MDC':#horizontal bg subtract
            difference_array1 = np.absolute(self.figures['right'].data[0] - self.figures['right'].cursor.sta_vertical_line.get_data()[0])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.figures['center'].data[3][index1:-1:,:],axis=0)
            new_int = self.figures['center'].data[3] - bg
            name = 'above_EF_MDC'
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'EDC':#EDC bg subtract
            pass
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'bg Matt':
            pass

        dict['data'] = new_int
        self.overview.data_handler.state_catalog.add_state(dict,'subtract_by:_'+name)
        self.figures['center'].click([self.figures['center'].cursor.sta_vertical_line.get_data()[0],self.figures['center'].cursor.sta_horizontal_line.get_data()[1]])#update the right and down figures

class Twodimension(Figure_handeler):#band
    def __init__(self,overview):
        super().__init__(overview)
        self.twoD = ['center']

    def make_figures(self):
        figures = {'center':figure.Band,'right':figure.DOS_right,'down':figure.DOS_down}
        positions = {'center':[self.pos[0],self.pos[1]],'right':[self.pos[0]+self.size[0],self.pos[1]],'down':[self.pos[0],self.pos[1]+self.size[1]]}
        self.figures = {}
        for key in figures.keys():
            self.figures[key] = figures[key](self,positions[key])#figures are initated here

    def fermi_level(self):#called when pressed the botton. corrects the fermi level based on a Au cut
        adjust = processing.Fermi_level_band(self.figures['center'])
        adjust.run()

    def kz_convert(self):#called when pressed the botton -> can be diabled if it is 2D?
        pass

    def symmetrise(self):#called when pressed the botton
        adjust = processing.Symmetrise(self.figures['center'])
        adjust.run()

    def normalise_slices(self):#only 3D data -> disable if it is 2D?
        pass

    def integrate(self):#it summs up the right and down figures
        self.figures['right'].int = np.sum(self.figures['center'].int,axis=1)/len(self.figures['center'].int[0,:])
        self.figures['down'].int = np.nansum(self.figures['center'].int,axis=0)/len(self.figures['center'].int)
        self.redraw()

    def EF_corr(self):#fermi level on one self
        adjust = processing.EF_corr(self.figures['center'])
        adjust.run()

    def make_circle(self):#only 3D data -> disable if it is 2D?
        pass

    def divide_by(self):#-2D data: it normalises the center figure by what is plotted in teh EDC or MDC, or read in a file
        dict = copy.deepcopy(self.overview.data_handler.file.data[self.overview.data_handler.file.index])
        if self.overview.operations.divide_by.configure('text')[-1] == '...':#reads in a ile and divide the center figure with this file
            ref_data, gold = self.overview.data_tab.data_loader.gold_please()
            if not ref_data: return
            temp = ref_data[0]['data'][0]#replace 0 with nan
            temp = temp.astype('float')
            temp[temp == 0] = np.nan

            result = self.figures['center'].data[-1][0] / temp

            dict['data'] = np.transpose(np.atleast_3d(result),(2,0,1))
            name = gold[gold.rfind('/')+1:]

        elif self.overview.operations.divide_by.configure('text')[-1] == 'MDC':
            dict['data'] = self.figures['center'].data[-1] / self.figures['right'].int[:, np.newaxis]
            name = 'MDC'
        elif self.overview.operations.divide_by.configure('text')[-1] == 'EDC':#EDC
            dict['data'] = self.figures['center'].data[-1] / self.figures['down'].int
            name = 'EDC'

        dict['data'] = np.nan_to_num(dict['data'],nan = 0.0)
        self.overview.data_handler.state_catalog.add_state(dict,'divided_by:_'+name)

    def normalise_cuts(self):#normalise the cuts to 1
        self.figures['right'].int =  self.figures['right'].int/np.nanmax(self.figures['right'].int)
        self.figures['down'].int =  self.figures['down'].int/np.nanmax(self.figures['down'].int)
        self.redraw()

    def subtract_by(self):
        dict = self.overview.data_handler.file.data[-1].copy()
        if self.overview.operations.BG_orientation.configure('text')[-1] == '...':#reads in a ile and divide the center figure with this file
            ref_data, gold = self.overview.data_tab.data_loader.gold_please()
            if not ref_data: return
            new_int = self.figures['center'].data[-1][0] - ref_data[0]['data'][0]
            name = gold[gold.rfind('/')+1:]
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'MDC':#horizontal bg subtract
            new_int = self.figures['center'].int - self.figures['right'].int[:,None]
            name = 'MDC'
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'EDC':#EDC bg subtract
            new_int = self.figures['center'].int - self.figures['down'].int[None,:]#subtract the EDC from each row in data
            name = 'EDC'
        elif self.overview.operations.BG_orientation.configure('text')[-1] == 'bg Matt':#EDC bg subtract
            new_int = self.figures['center'].int.copy()
            name = 'BG_Matt'
            for index, ary in enumerate(np.transpose(self.figures['center'].int[0:-1,:])):#MDCs -> deifine the area...
                new_int[:,index] -= np.nanmin(ary)#take the average of a couple of miniums?

        dict['data'] =np.transpose(np.atleast_3d(new_int),(2,0,1))

        self.overview.data_handler.state_catalog.add_state(dict,'subtract_by:_'+name)
        self.figures['center'].click([self.figures['center'].cursor.sta_vertical_line.get_data()[0],self.figures['center'].cursor.sta_horizontal_line.get_data()[1]])#update the right and down figures
