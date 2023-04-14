import numpy as np
import sys

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

class Fermi_adjusted(States):
    def __init__(self,figure):
        super().__init__(figure)

    def click_right(self,difference_array):
        index1 = np.argmin(difference_array,axis=1)
        return index1[0]

    def click_down(self,difference_array):
        index2 = np.argmin(difference_array)
        self.figure.sub_tab.down.data[0] = self.figure.data[0][index2]
        return index2

class K_space(States):
    def __init__(self,figure):
        super().__init__(figure)

    def click_right(self,difference_array):
        index1 = np.argmin(difference_array,axis=1)
        return index1[0]

    def click_down(self,difference_array):
        index2 = np.argmin(difference_array)
        self.figure.sub_tab.down.data[0] = self.figure.data[0][index2]
        return index2

    def difference_array(self,pos):
        return np.absolute(self.figure.data[1][:,0]-pos)
