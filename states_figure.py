import numpy as np
import sys

#the state of the figure. The state is define if there have been operations on the figures (i.e. raw, fermi adjusted, k space)
class States():
    def __init__(self,figure):
        self.figure = figure

    def click_right(self,difference_array):
        pass

    def click_down(self,difference_array):
        return np.argmin(difference_array)

    def enter_state(self,newstate):
        self.figure.state = getattr(sys.modules[__name__], newstate)(self.figure)#make a class based on the name of the newstate: need to import sys

class Raw(States):
    def __init__(self,figure):
        super().__init__(figure)

    def click_right(self,difference_array):
        return np.argmin(difference_array)

    def difference_array(self,pos):
        return np.absolute(self.figure.data[1]-pos)

    def bg_subtract(self):
        if self.figure.sub_tab.operations.checkbox['vertical'].get():#vertical bg subtract
            difference_array1 = np.absolute(self.figure.data[1] - self.figure.cursor.sta_horizontal_line.get_data()[1])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.figure.int[index1:-1,:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
            self.figure.int -=  bg
        else:#horizontal bg subtract
            difference_array1 = np.absolute(self.figure.data[0] - self.figure.cursor.sta_vertical_line.get_data()[0])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.figure.int[:,index1:-1],axis=1)#axis = 0is vertical, axis =1 is horizontal means
            int = np.transpose(self.figure.int)
            int -=  bg
            self.figure.int = np.transpose(int)

class Fermi_adjusted(States):
    def __init__(self,figure):
        super().__init__(figure)

    def click_right(self,difference_array):
        index1 = np.argmin(difference_array,axis=1)
        return index1[0]

    def click_down(self,difference_array):
        index2 = np.argmin(difference_array)
        self.figure.down.data[0] = self.figure.data[0][index2]
        return index2

    def bg_subtract(self):
        if self.figure.sub_tab.operations.checkbox['vertical'].get():#vertical bg subtract
            difference_array1 = np.absolute(self.figure.data[1] - self.figure.cursor.sta_horizontal_line.get_data()[1])
            index1 = np.argmin(difference_array1,axis=1)
            bg = np.nanmean(self.figure.int[index1:-1,:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
            self.figure.int -=  bg
        else:#horizontal bg subtract
            difference_array1 = np.absolute(self.figure.data[0] - self.figure.cursor.sta_vertical_line.get_data()[0])
            index1 = np.argmin(difference_array1,axis=1)[0]
            bg = np.nanmean(self.figure.int[:,index1:-1],axis=1)#axis = 0is vertical, axis =1 is horizontal means
            int = np.transpose(self.figure.int)
            int -=  bg
            self.figure.int = np.transpose(int)

class K_space(States):
    def __init__(self,figure):
        super().__init__(figure)

    def click_right(self,difference_array):
        index1 = np.argmin(difference_array)
        return index1

    def click_down(self,difference_array):
        index2 = np.argmin(difference_array)
        return index2

    def difference_array(self,pos):
        return np.absolute(self.figure.data[1][:,0]-pos)

    def bg_subtract(self):
        if self.figure.sub_tab.operations.checkbox['vertical'].get():#vertical bg subtract
            difference_array1 = np.absolute(self.figure.data[1] - self.figure.cursor.sta_horizontal_line.get_data()[1])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.figure.int[index1:-1,:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
            self.figure.int -=  bg
        else:#horizontal bg subtract
            difference_array1 = np.absolute(self.figure.data[0] - self.figure.cursor.sta_vertical_line.get_data()[0])
            index1 = difference_array1.argmin()
            bg = np.nanmean(self.figure.int[:,index1:-1],axis=1)#axis = 0is vertical, axis =1 is horizontal means
            int = np.transpose(self.figure.int)
            int -=  bg
            self.figure.int = np.transpose(int)        
