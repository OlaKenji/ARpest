import numpy as np
import tkinter as tk

import figure, cursor
from scipy import ndimage
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from scipy import interpolate
import data_loader

class Raw():
    def __init__(self,figure):
        self.figure = figure
        self.original_int = self.figure.int.copy()
        self.define_mouse()
        #self.figure.state.enter_state('Raw')

    def define_mouse(self):
        self.figure.define_mouse()

    def exit(self):
        pass

    def run(self):
        self.figure.int = self.original_int.copy()

class Derivative_x(Raw):
    def __init__(self,figure):
        super().__init__(figure)
        self.slides = []
        self.slide_cx()
        self.slide_cy()
        self.slide_dx()
        self.slide_dy()

        self.cx = 1
        self.cy = 1
        self.dx = 0.001
        self.dy = 0.001
        self.direction = 'x'#smooth direction

    def exit(self):
        self.figure.int = self.original_int.copy()
        for slide in self.slides:
            slide.destroy()#remove the slides

    def slide_cx(self):
        scale = tk.Scale(self.figure.sub_tab.tab,from_=0,to=10,orient = tk.HORIZONTAL,label='cx',command=self.update_cx,resolution=0.1)
        scale.pack()
        self.slides.append(scale)

    def slide_cy(self):
        scale = tk.Scale(self.figure.sub_tab.tab,from_=0,to=10,orient = tk.HORIZONTAL,label='cy',command=self.update_cy,resolution=0.1)
        scale.pack()
        self.slides.append(scale)

    def slide_dx(self):
        scale = tk.Scale(self.figure.sub_tab.tab,from_=0,to=10,orient = tk.HORIZONTAL,label='dx',command=self.update_dx,resolution=0.1)
        scale.pack()
        self.slides.append(scale)

    def slide_dy(self):
        scale = tk.Scale(self.figure.sub_tab.tab,from_=0,to=10,orient = tk.HORIZONTAL,label='dy',command=self.update_dy,resolution=0.1)
        scale.pack()
        self.slides.append(scale)

    def update_cx(self,value):
        self.cx = float(value)
        self.run()
        self.figure.draw()

    def update_cy(self,value):
        self.cy = float(value)
        self.run()
        self.figure.draw()

    def update_dx(self,value):
        self.dx = float(value)
        self.run()
        self.figure.draw()

    def update_dy(self,value):
        self.dy = float(value)
        self.run()
        self.figure.draw()

    def smooth(self,data,kernel_size = 50):
        direction={'x':-1,'y':0}[self.direction]
        kern = np.hanning(kernel_size)   # a Hanning window with width 50
        kern /= kern.sum()      # normalize the kernel weights to sum to 1
        smooth_data = ndimage.convolve1d(data, kern, axis = direction)#axis =0 is y, axis = -1 is x
        return smooth_data

    @staticmethod
    def derivatives(data,dx,dy):
    # The `axis` arguments change depending on the shape of the input data
        d = len(data.shape)
        axis0 = 0 if d==2 else 1

        # Calculate the derivatives in both directions
        grad_x = np.gradient(data, dx, axis=axis0)
        grad_y = np.gradient(data, dy, axis=axis0+1)

        # And the second derivatives...
        grad2_x = np.gradient(grad_x, dx, axis=axis0)
        grad2_y = np.gradient(grad_y, dy, axis=axis0+1)

        return grad_x, grad_y, grad2_x, grad2_y

    def run(self):#DOI: 10.1063/1.3585113
        data = self.original_int.copy()
        smooth_data = self.smooth(data)

        grad_x, grad_y, grad2_x, grad2_y = self.derivatives(smooth_data, self.dx, self.dy)

        # We also need the mixed derivative
        axis = 1 if len(data.shape)==2 else 2
        grad_xy = np.gradient(grad_x, self.dy, axis=axis)

        # And the squares of first derivatives
        grad_x2 = grad_x**2
        grad_y2 = grad_y**2

        # Build the nominator
        nominator  = (1 + self.cx*grad_x2)*self.cy*grad2_y
        nominator += (1 + self.cy*grad_y2)*self.cx*grad2_x
        nominator -= 2 * self.cx * self.cy * grad_x * grad_y * grad_xy

        # And the denominator
        denominator = (1 + self.cx*grad_x2 + self.cy*grad_y2)**(1.5)

        # Return the curvature
        self.figure.int =  nominator / denominator#np.clip(intensity,0,1000)

    def run2(self):#numpy method
        d = len(self.figure.int.shape)
        if d == 2:
            axis0 = 0
        else:
            axis0 = 1

        smooth_data = self.smooth(self.figure.int)

        #1st derivatives in both directions
        data1_x = np.gradient(smooth_data, axis=axis0)
        data1_y = np.gradient(smooth_data, axis=axis0+1)

        # 2nd derivatives in both directions
        data2_x  = np.gradient(data1_x, axis=axis0)
        data2_y = np.gradient(data1_y, axis=axis0+1)

        self.set_values(data2_x,data2_y)

    def smooth2(self,data,kernel_size = 20):#not as good
        kernel = np.ones(kernel_size) / kernel_size
        smooth_data = data#place holrder
        if self.direction == 'x':#smooth in x direction
            for index, row in enumerate(data):
                smooth_data[index] = np.convolve(row, kernel, mode='same')
        elif self.direction == 'y':#smooth in y direction
            for i in range(0,len(data[0])):
                col=data[:,i]
                smooth_data[:,i] = np.convolve(col, kernel, mode='same')
        return smooth_data

    def set_values(self,data2_x,data2_y):
        self.figure.int = data2_x

class Derivative_y(Derivative_x):
    def __init__(self,figure):
        super().__init__(figure)
        self.direction = 'y'#smooth direction

    def set_values(self,data2_x,data2_y):
        self.figure.int = data2_y

class Convert_k(Raw):
    def __init__(self,figure):
        super().__init__(figure)
        #self.figure.state.enter_state('K_space')
        self.hv = self.figure.sub_tab.data.metadata['hv']

    def run(self):
        self.convert2k()
        self.update_figure()

    def update_figure(self):
        self.figure.figure_handeler.update_sort_data()#update the cuts, but avoid for main figure
        #self.figure.figure_handeler.update_intensity()
        self.figure.figure_handeler.draw()
        self.figure.figure_handeler.update_mouse_range()

    def convert2k(self):
        work_func = 4#usually 4
        k0 = 0.5124 * np.sqrt(self.hv - work_func)

        #alpha is the polar or theta
        #beta is the tilt

        # Angle to radian conversion
        dalpha,dbeta = 0,0
        alpha,beta = self.figure.define_angle2k()#depends on the figure
        a = (alpha+dalpha)*np.pi/180
        b = (beta+dbeta)*np.pi/180

        # place hodlers
        nkx = len(alpha)
        nky = len(beta)
        KX = np.empty((nkx, nky))
        KY = np.empty((nkx, nky))

        if self.figure.sub_tab.data_tab.data_loader.orientation == 'horizontal':
            for i in range(nkx):
                KX[i] = np.sin(b) * np.cos(a[i])
                KY[i] = np.sin(a[i])

        elif self.figure.sub_tab.data_tab.data_loader.orientation == 'vertical':
            # Precalculate outside the loop
            theta_k = beta*np.pi/180
            cos_theta = np.cos(theta_k)
            sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta*np.pi/180)
            for i in range(nkx):
                KX[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * \
                        np.sin(dbeta*np.pi/180)
                KY[i] = cos_theta * np.sin(a[i])


        if KY.shape[1] == 1:#2D, band
            self.figure.data[1] = np.linspace(k0*KY.min(), k0*KY.max(),len(KY.ravel()))
        else:#3D, FS
            self.new_mesh(k0*KX,k0*KY)

    def exit(self):
        self.figure.sort_data()
        self.figure.draw()

    def new_mesh(self,kx,ky):#for 3D data set, FS, correct only the current level
        min_index = [np.argmin((kx[:,-1]-kx[:,0])),np.argmin((ky[-1]-ky[0]))]#the index in whihc there is the minimum distance between the intensity mesh

        #min_distance = [kx[index[0]][1]-kx[index[0]][0], ky[1][index[1]]-ky[0][index[1]]]#minimum bin size
        min_bin = [(np.amax(kx[min_index[0]]) - np.amin(kx[min_index[0]]))/len(kx[min_index[0]]),(np.amax(ky[:,min_index[1]]) - np.amin(ky[:,min_index[1]]))/len(ky[:,min_index[1]])]#min bin size

        max_index = [np.argmax((kx[:,-1]-kx[:,0])),np.argmax((ky[-1]-ky[0]))]#the index in whihc there is the max distance betwene the intensitie mesh
        max_distance = [np.amax(kx[max_index[0]]) - np.amin(kx[max_index[0]]),np.amax(ky[:,max_index[1]]) - np.amin(ky[:,max_index[1]])]
        number = [max_distance[0]/min_bin[0],max_distance[1]/min_bin[1]]

        axis_y = np.linspace(np.amin(ky[:,max_index[1]]),np.amax(ky[:,max_index[1]]),num = int(number[1]))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_x =np.linspace(np.amin(kx[max_index[0]]),np.amax(kx[max_index[0]]),num = int(number[0]))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance

        #reshape the intensity
        intensity = np.zeros((len(axis_y),len(axis_x)))#place holder for mesh
        inrange = False#a flag to check if in range
        for col, x_cord in enumerate(axis_x):
            index_real = [0,0]#the index of the kspace coordinates
            for row,y_cord in enumerate(axis_y):#from below
                if y_cord < ky[index_real[1]][col]:#below
                    real_int = np.NaN
                    if inrange:
                        real_int = self.figure.int[index_real[1]][col]
                elif y_cord > ky[-1][col]:#above
                    inrange = False
                    real_int = np.NaN
                else:#if bigger
                    real_int = self.figure.int[index_real[1]][col]
                    index_real[1] += 1
                    inrange = True

                intensity[row][col] = real_int

        self.figure.int = intensity
        self.figure.data[0] = axis_x
        self.figure.data[1] = axis_y

    def new_mesh2(self,kx,ky):#for 3D data set, it corrects for every energy level: takes time
        min_index = [np.argmin((kx[:,-1]-kx[:,0])),np.argmin((ky[-1]-ky[0]))]#the index in whihc there is the minimum distance between the intensity mesh

        #min_distance = [kx[index[0]][1]-kx[index[0]][0], ky[1][index[1]]-ky[0][index[1]]]#minimum bin size
        min_bin = [(np.amax(kx[min_index[0]]) - np.amin(kx[min_index[0]]))/len(kx[min_index[0]]),(np.amax(ky[:,min_index[1]]) - np.amin(ky[:,min_index[1]]))/len(ky[:,min_index[1]])]#min bin size

        max_index = [np.argmax((kx[:,-1]-kx[:,0])),np.argmax((ky[-1]-ky[0]))]#the index in whihc there is the max distance betwene the intensitie mesh
        max_distance = [np.amax(kx[max_index[0]]) - np.amin(kx[max_index[0]]),np.amax(ky[:,max_index[1]]) - np.amin(ky[:,max_index[1]])]
        number = [max_distance[0]/min_bin[0],max_distance[1]/min_bin[1]]

        axis_y = np.linspace(np.amin(ky[:,max_index[1]]),np.amax(ky[:,max_index[1]]),num = int(number[1]))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_x = np.linspace(np.amin(kx[max_index[0]]),np.amax(kx[max_index[0]]),num = int(number[0]))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance
        axis_z = self.figure.data[2]

        #reshape the intensity, every energy
        intensity = np.zeros((len(axis_z),len(axis_y),len(axis_x)))#place holder for mesh
        for index_z, z in enumerate(axis_z):
            inrange = False#a flag to check if in range
            for col, x_cord in enumerate(axis_x):
                index_real = [0,0]#the index of the kspace coordinates
                for row,y_cord in enumerate(axis_y):#from below
                    if y_cord < ky[index_real[1]][col]:#below
                        real_int = np.NaN
                        if inrange:
                            real_int = self.figure.data[3][index_z][index_real[1]][col]
                    elif y_cord > ky[-1][col]:#above
                        inrange = False
                        real_int = np.NaN
                    else:#if bigger
                        real_int = self.figure.data[3][index_z][index_real[1]][col]
                        index_real[1] += 1
                        inrange = True

                    intensity[index_z][row][col] = real_int

        self.figure.int = intensity[0]
        self.figure.data[0] = axis_x
        self.figure.data[1] = axis_y
        self.figure.data[3] = intensity

class Convert_kz(Raw):
    def __init__(self,figure):
        super().__init__(figure)
        #self.figure.state.enter_state('K_space')

    def run(self):
        self.converthv()
        self.update_figure()

    def update_figure(self):
        self.figure.figure_handeler.update_intensity()#update the cuts, but avoid for main figure
        self.figure.figure_handeler.update_sort_data()#update the cuts, but avoid for main figure
        self.figure.figure_handeler.draw()
        self.figure.figure_handeler.update_mouse_range()

    def converthv(self):
        #convert to kz
        q = 1.60218*10**-19#charge
        m = 9.1093837*10**-31#kg
        hbar = (6.62607015*10**-34)/(2*np.pi)#m2 kg / s
        V = 8*q#J
        W = 4.5#eV
        Eb = 0#eV binding energy
        kz = []
        ky = []
        for hv in self.figure.data[0]:#do it for each photon energy
            ky.append(self.convert2k(hv)[:,0])
            Ek = (hv-W-Eb)*q#J -> can be extract the value from the figure?
            theta = self.figure.data[1]
            kz.append(10**-10*np.sqrt(2*m*(Ek*np.cos(np.pi*theta/180)**2+V))/hbar)

        kz = np.transpose(np.array(kz))
        ky = np.transpose(np.array(ky))
        #print(ky,kz)

        #self.figure.data[0] = kz
        #self.figure.data[1] = ky

        #new mesh
        self.new_mesh_interpolation(kz,ky)

    def new_mesh_manual_interpolation(self,kx,ky):
        min_index = [np.argmin(kx[:].max(axis=0)-kx[:].min(axis=0)),np.argmin(ky[:].max(axis=0)-ky[:].min(axis=0))]#the index in whihc there is the minimum distance between the intensity mesh

        length = np.argmax(kx[:,min_index[0]])-np.argmin(kx[:,min_index[0]])
        min_bin = [(np.amax(kx[:,min_index[0]]) - np.amin(kx[:,min_index[0]]))/length,(np.amax(ky[:,min_index[1]]) - np.amin(ky[:,min_index[1]]))/len(ky[:])]#min bin size

        #max_index = [np.argmax((kx[:,-1]-kx[:,0])),np.argmax((ky[-1]-ky[0]))]#the index in whihc there is the max distance betwene the intensitie mesh
        max_distance = [kx.max() - kx.min(),ky.max() - ky.min()]
        number = [max_distance[0]/min_bin[0],max_distance[1]/min_bin[1]]

        axis_y = np.linspace(ky.min(),ky.max(),num = round(number[1]))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_x =np.linspace(kx.min(),kx.max(),num = round(number[0]))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance

        data = np.zeros((len(axis_y),len(axis_x)))#place holder for mesh
        data[:] = np.NaN
        index=[0,0]

        #bascially workds but not perfect
        for row_index, row in enumerate(kx):
            for col, x in enumerate(row):
                y = ky[row_index][col]
                #translate to appropriate positions
                index[0] = (x - axis_x[0])/min_bin[0]
                index[1] = (y - axis_y[0])/min_bin[1]
                index[0] = min(index[0],3419)#fix this
                data[int(index[1])][int(index[0])] = self.figure.int[row_index][col]

        #manual interpolation

        #theoretical conversion
        kz_theory = []
        theta = np.linspace(self.figure.data[1].min(),self.figure.data[1].max(),num=len(axis_y))

        q = 1.60218*10**-19#charge
        m = 9.1093837*10**-31#kg
        hbar = (6.62607015*10**-34)/(2*np.pi)#m2 kg / s
        V = 8*q#J
        W = 4.5#eV
        Eb = 0#eV binding energy
        hvs=self.figure.data[0]
        hvs=np.append(hvs,self.figure.data[0][-1]+2)
        for hv in hvs:#do it for each photon energy
            Ek = (hv-W-Eb)*q#J -> can be extract the value from the figure?
            kz_theory.append(10**-10*np.sqrt(2*m*(Ek*np.cos(np.pi*theta/180)**2+V))/hbar)


        kz_theory = np.transpose(np.array(kz_theory))
        theta = np.transpose(np.array(theta))
        #plt.plot(kz_theory,theta)
        #plt.show()
        #theoretical border
        new_data = data
        index = [0,0]#pointer
        for row, y_cord in enumerate(axis_y):
            for col, x_cord in enumerate(axis_x):
                for column in range(len(kz_theory[0])-1):#for each hv
                    real_intensiry = np.NaN
                    if x_cord >= kz_theory[row][column] and x_cord < kz_theory[row][column+1]:
                        index_x = np.absolute(kx[:,column] - x_cord).argmin()
                        index_y = np.absolute(ky[:,column] - y_cord).argmin()
                        #print(index_x,index_y)
                        real_intensiry = self.figure.int[index_y][column]
                        break


                new_data[row][col] = real_intensiry

        #save the results
        self.figure.int = new_data
        self.figure.data[0] = axis_x
        self.figure.data[1] = axis_y

    def new_mesh_interpolation(self,kx,ky):
        min_index = [np.argmin(kx[:].max(axis=0)-kx[:].min(axis=0)),np.argmin(ky[:].max(axis=0)-ky[:].min(axis=0))]#the index in whihc there is the minimum distance between the intensity mesh

        length = np.argmax(kx[:,min_index[0]])-np.argmin(kx[:,min_index[0]])
        min_bin = [(np.amax(kx[:,min_index[0]]) - np.amin(kx[:,min_index[0]]))/length,(np.amax(ky[:,min_index[1]]) - np.amin(ky[:,min_index[1]]))/len(ky[:])]#min bin size

        #max_index = [np.argmax((kx[:,-1]-kx[:,0])),np.argmax((ky[-1]-ky[0]))]#the index in whihc there is the max distance betwene the intensitie mesh
        max_distance = [kx.max() - kx.min(),ky.max() - ky.min()]
        number = [max_distance[0]/min_bin[0],max_distance[1]/min_bin[1]]

        axis_y = np.linspace(ky.min(),ky.max(),num = round(number[1]))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_x =np.linspace(kx.min(),kx.max(),num = round(number[0]))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance

        data = np.zeros((len(axis_y),len(axis_x)))#place holder for mesh
        data[:] = np.NaN
        index=[0,0]

        #bascially workds but not perfect
        for row_index, row in enumerate(kx):
            for col, x in enumerate(row):
                y = ky[row_index][col]
                #translate to appropriate positions
                index[0] = (x - axis_x[0])/min_bin[0]
                index[1] = (y - axis_y[0])/min_bin[1]
                index[0] = min(index[0],3419)#fix this
                data[int(index[1])][int(index[0])] = self.figure.int[row_index][col]

        #interpolate
        xx, yy = np.meshgrid(axis_x, axis_y)
        masked_intensity = np.ma.masked_invalid(data)
        intensity= interpolate.griddata((xx[~masked_intensity.mask],yy[~masked_intensity.mask]), masked_intensity[~masked_intensity.mask].ravel(),(xx, yy),method='linear')

        #save the results
        self.figure.int = intensity
        self.figure.data[0] = axis_x
        self.figure.data[1] = axis_y

        return#below is for every energy. Very slow....

        axis_z = self.figure.data[2]

        data = np.zeros((len(axis_z),len(axis_y),len(axis_x)))#place holder for mesh
        data[:] = np.NaN
        index=[0,0]

        #bascially workds but not perfect
        for index_z, z in enumerate(axis_z):
            for row_index, row in enumerate(kx):
                for col, x in enumerate(row):
                    y = ky[row_index][col]
                    #translate to appropriate positions
                    index[0] = (x - axis_x[0])/min_bin[0]
                    index[1] = (y - axis_y[0])/min_bin[1]
                    index[0] = min(index[0],3419)
                    data[index_z][int(index[1])][int(index[0])] = self.figure.data[3][index_z][row_index][col]

        #this works but insainly slow, works for up to 7 files, maybe?
        intensity = []
        xx, yy = np.meshgrid(axis_x, axis_y)
        for layer in data:
            masked_intensity = np.ma.masked_invalid(layer)
            intensity.append(interpolate.griddata((xx[~masked_intensity.mask],yy[~masked_intensity.mask]), masked_intensity[~masked_intensity.mask].ravel(),(xx, yy),method='linear'))

        self.figure.int = intensity[0]
        self.figure.data[0] = axis_x
        self.figure.data[1] = axis_y
        self.figure.data[3] = intensity

        return

        #this also works but is even lower...
        new_intensity=np.array(data[0])
        xx, yy = np.meshgrid(axis_x, axis_y)
        for index, layer in enumerate(data):
            intensity=np.array([layer[0]])

            for col,array in enumerate(layer):
                masked_intensity = np.ma.masked_invalid(array)
                int2 = np.interp(axis_x,axis_x[~masked_intensity.mask],masked_intensity[~masked_intensity.mask])

                intensity = np.append(intensity, [int2], axis=0)

                if col == 0:
                    intensity = np.delete(intensity, len(intensity)-1, 0)
            new_intensity=np.dstack((new_intensity,intensity))

        self.figure.int = new_intensity[0]
        self.figure.data[0] = axis_x
        self.figure.data[1] = axis_y
        self.figure.data[3] = new_intensity

    def convert2k(self,hv):
        work_func = 4#usually 4
        hv = hv#incident energy
        k0 = 0.5124 * np.sqrt(hv - work_func)

        #alpha is the polar or theta
        #beta is the tilt

        # Angle to radian conversion
        dalpha,dbeta = 0,0
        alpha,beta = self.figure.define_hv()#depends on the figure
        a = (alpha+dalpha)*np.pi/180
        b = (beta+dbeta)*np.pi/180

        # place hodlers
        nkx = len(alpha)
        nky = len(beta)
        KX = np.empty((nkx, nky))
        KY = np.empty((nkx, nky))

        if self.figure.sub_tab.slit == 'h':
            for i in range(nkx):
                KX[i] = np.sin(b) * np.cos(a[i])
                KY[i] = np.sin(a[i])

        elif self.figure.sub_tab.slit == 'v':
            # Precalculate outside the loop
            theta_k = beta*np.pi/180
            cos_theta = np.cos(theta_k)
            sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta*np.pi/180)
            for i in range(nkx):
                KX[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * \
                        np.sin(dbeta*np.pi/180)
                KY[i] = cos_theta * np.sin(a[i])

        return k0*KY
        #if KY.shape[1] == 1:#2D, band
        #    self.figure.data[1] = np.linspace(k0*KY.min(), k0*KY.max(),len(KY.ravel()))
        #else:#3D, FS
        #    self.new_mesh(k0*KX,k0*KY)

    def exit(self):
        self.figure.sort_data()
        self.figure.draw()

class Fermi_level_band(Raw):#only the main figure
    def __init__(self,parent_figure):
        super().__init__(parent_figure)
        gold = tk.filedialog.askopenfilename(initialdir=self.figure.sub_tab.data_tab.gui.start_path ,title='gold please')
        self.gold = self.figure.sub_tab.data_tab.data_loader.load_data(gold)
        self.kB = 1.38064852e-23 #[J/K]
        self.eV = 1.6021766208e-19#[J]
        self.hv = self.figure.sub_tab.data.metadata['hv']
        self.e_0 = self.hv - 4.38#initial guess of fermi level
        #self.figure.state.enter_state('Fermi_adjusted')

    def run(self):
        self.figure.gold()#cannot be in init
        self.fit()
        self.pixel_shift()
        self.update_figure()

    def update_figure(self):
        self.figure.figure_handeler.update_intensity()#update the cuts, but avoid for main figure
        self.figure.figure_handeler.update_sort_data()#update the cuts, but avoid for main figure -> this is not wokring if you do k space first since the FS will be a 2D arrat, while band wants 1D
        self.figure.figure_handeler.draw()
        self.figure.figure_handeler.update_mouse_range()

    def pixel_shift(self):#pixel ashift and add NaN such that the index of the fermilevel allign along x in the data
        energies = self.figure.data[0]
        fermi_levels = self.EF
        fermi_index = np.array([np.argmin(np.abs(energies - f)) for f in fermi_levels],dtype=int)

        max_shift = max(fermi_index)-min(fermi_index)
        new_data = np.array([energies - level for level in fermi_levels])#shifted data#s
        target_index = max(fermi_index)


        dE = energies[1] - energies[0]

        new_array = np.zeros((len(fermi_levels),len(new_data[0])+max_shift))#place holder
        new_intensity = np.zeros((len(fermi_levels),len(new_data[0])+max_shift))#place holder
        new_intensity[:] =  np.nan
        intensity = self.figure.int

        for row, array in enumerate(new_data):
            shift = target_index - fermi_index[row]
            if shift != 0:#insert at the begnning
                empty_1 = np.empty(shift)
                empty_1[:] = array[0]
                array = np.insert(array,0,empty_1)
                empty_1[:] = np.nan
                temp = np.insert(intensity[row],0,empty_1)
            else:
                temp = intensity[row]

            #insert at the end
            more_shift = max_shift - shift
            empty_1 = np.empty(more_shift)
            empty_1[:] = array[-1]
            array = np.append(array,empty_1)
            empty_1[:] = np.nan
            temp = np.append(temp,empty_1)

            new_array[row] = array
            new_intensity[row] = temp

        new_axis = np.linspace(new_array.min(), new_array.max(),len(new_intensity[0,:]))

        self.figure.data[0] = new_axis
        self.figure.int = new_intensity

    def fit(self):
        e_0 = self.hv - 4.38#femi level guess
        T = 10#K

        gold = self.gold.data[0]
        n_pixels, n_energies = gold.shape
        energies = self.gold.xscale

        params = []
        functions = []
        for i,edc in enumerate(gold):
            p, res_func = self.fit_fermi_dirac(energies, edc, self.e_0, T=T)
            params.append(p)
            self.e_0 = p[0]#update teh guess
            functions.append(res_func)

        # Prepare the results
        params = np.array(params)
        fermi_levels = params[:,0]
        sigmas = params[:,1]
        slopes = params[:,2]
        offsets = params[:,3]

        self.EF = fermi_levels
        #return fermi_levels, sigmas, slopes, offsets, functions

    def fit_fermi_dirac(self,energies,edc,e_0,T=10, sigma0=1, a0=0, b0=-0.1):
        # Normalize the EDC to interval [0, 1]
        edcmin = edc.min()
        edcmax = edc.max()
        edc = (edc-edcmin)/(edcmax-edcmin)

        # Initial guess and bounds for parameters
        p0 = [e_0, sigma0, a0, b0]
        de = 1
        lower = [e_0-de, 0, -10, -1]
        upper = [e_0+de, 100, 10, 1]

        # Carry out the fit
        p, cov = curve_fit(self.FD_function, energies, edc, p0=p0, bounds=(lower, upper))

        res_func = lambda x : self.FD_function(x, *p)
        return p, res_func

    def FD_function(self,E, E_F, sigma, a, b, T=10):
        # Basic Fermi Dirac distribution at given T
        sigma =0
        kT = self.kB * T / self.eV
        y = 1 / (np.exp((E-E_F)/kT) + 1)

        # Add a linear contribution to the 'below-E_F' part
        y += (a*(E-E_F)+b) * self.step_function(E, E_F, flip=True)

        # Convolve with instrument resolution
        if sigma > 0 :
            y = ndimage.gaussian_filter(y, sigma)
        return y

    def step_function(self,x, step_x, flip) :
        res = \
        np.frompyfunc(lambda x : self.step_function_core(x, step_x, flip), 1, 1)(x)
        return res.astype(float)

    def step_function_core(self,x, step_x, flip) :
        """ Implement a perfect step function f(x) with step at `step_x`::

                    / 0   if x < step_x
                    |
            f(x) = {  0.5 if x = step_x
                    |
                    \ 1   if x > step_x

        **Parameters**

        ======  ====================================================================
        x       array; x domain of function
        step_x  float; position of the step
        flip    boolean; Flip the > and < signs in the definition
        ======  ====================================================================
        """
        sign = -1 if flip else 1
        if sign*x < sign*step_x :
            result = 0
        elif x == step_x :
            result = 0.5
        elif sign*x > sign*step_x :
            result = 1
        return result

class Fermi_level_FS(Fermi_level_band):#only the main figure
    def __init__(self,parent_figure):
        super().__init__(parent_figure)

    def pixel_shift(self):#pixel ashift and add NaN such that the index of the fermilevel allign along x in the data
        energies = self.figure.data[2]#the energies, the z axis
        fermi_levels = self.EF
        fermi_index = np.array([np.argmin(np.abs(energies - f)) for f in fermi_levels],dtype=int)
        print('lets shift')
        max_shift = max(fermi_index)-min(fermi_index)
        new_data = np.array([energies - level for level in fermi_levels])#shifted data#s
        target_index = max(fermi_index)

        new_array = np.zeros((len(fermi_levels),len(new_data[0])+max_shift))#place holder
        intensity = self.figure.data[3]

        NaN = []
        for i in range(len(intensity[0][0])):
            NaN.append(np.NaN)
        NaN = np.array(NaN)
        new_intensity = []

        #intensity = np.append(intensity,np.transpose(np.atleast_3d(NaN)),axis=0)
        for index in range(len(fermi_index)):
            slice = intensity[:,index,:]
            array = new_data[index]

            shift = target_index - fermi_index[index]
            if shift != 0:#insert at the begnning
                empty_1 = np.empty(shift)
                empty_1[:] = array[0]
                array = np.insert(array,0,empty_1)
            for i in range(0,shift):
                slice = np.insert(slice,0,NaN,0)#0 is th eaxis

            #insert at the end
            more_shift = max_shift - shift
            empty_1 = np.empty(more_shift)
            empty_1[:] = array[-1]
            array = np.append(array,empty_1)
            for i in range(0,more_shift):
                slice = np.vstack((slice,NaN))

            new_intensity.append(slice)
            new_array[index] = array

        dE = energies[1] - energies[0]
        #new_axis = np.arange(new_array.min(), new_array.max()+dE, dE)

        new_intensity = np.array(new_intensity)
        new_axis = np.linspace(new_array.min(), new_array.max(),len(new_intensity[0,:,0]))

        self.figure.data[2] = new_axis
        self.figure.data[3] = np.transpose(new_intensity, (1, 0, 2))

class Range_plot(Raw):
    def __init__(self,parent_figure):
        super().__init__(parent_figure)
        self.slide_limits = [0,5]
        self.define_slide()
        self.define_entry()
        pos = [300,0]
        self.fig = figure.DOS_down(self.figure.sub_tab,pos)

    def define_slide(self):
        self.scale = tk.Scale(self.figure.sub_tab.tab,from_=self.slide_limits[0],to=self.slide_limits[1],orient=tk.HORIZONTAL,command=self.update_range,resolution=1)
        self.scale.pack()

    def update_range(self,value):
        range = (self.figure.ylimits[1]-self.figure.ylimits[0])*(1/self.slide_limits[1])*0.5
        self.figure.sub_tab.range = int(value)*range
        self.figure.cursor.draw_sta_line()

    def define_mouse(self):
        self.figure.cursor = cursor.Range_cursor(self.figure)
        self.figure.canvas.get_tk_widget().bind( "<Motion>", self.figure.cursor.on_mouse_move)#move
        self.figure.canvas.get_tk_widget().bind( "<B1-Motion>", self.figure.cursor.drag)#left click

    def define_entry(self):
        self.e1 = tk.Entry(self.figure.sub_tab.tab,width=5)#the step size
        offset=[140,50]
        self.e1.place(x = self.figure.pos[0] + offset[0], y = self.figure.pos[1] + offset[1])
        self.e1.insert(0, 10)#default value 1

    def run(self):#the method: plot the stuff
        pos=self.figure.cursor.get_position()
        stepsize=int(self.e1.get())
        difference_array = np.absolute(self.figure.data[1]-pos[0])
        index1 = int(difference_array.argmin())

        difference_array = np.absolute(self.figure.data[1]-pos[1])
        index2 = int(difference_array.argmin())
        number = round((index2 - index1)/stepsize)

        self.fig.ax.cla()
        for i in range(0,number):
            self.fig.intensity(index1)
            #self.fig.draw()
            self.fig.plot()
            self.fig.canvas.draw()
            index1 += stepsize
        self.fig.curr_background = self.fig.canvas.copy_from_bbox(self.fig.ax.bbox)

    def exit(self):
        del self.fig#doesn'r work
        self.scale.destroy()
        self.e1.destroy()
