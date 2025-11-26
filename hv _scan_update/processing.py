import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt

import figure, cursor#for range plot
from scipy import ndimage
from scipy.optimize import curve_fit
from scipy import interpolate
import data_loader
import copy

class Raw():
    def __init__(self,figure):
        self.figure = figure
        self.original_int = self.figure.int.copy()

    def exit(self):
         pass

    def run(self):
        self.figure.int = self.original_int.copy()

class Smooth(Raw):
    def __init__(self,figure,direction):
        super().__init__(figure)
        self.direction = direction

    def run(self, kernel_size = 40):
        data = self.figure.int
        direction={'horizontal':-1,'vertical':0}[self.direction]
        kern = np.hanning(kernel_size)   # a Hanning window with width 50
        kern /= kern.sum()      # normalize the kernel weights to sum to 1
        smooth_data = ndimage.convolve1d(data, kern, axis = direction)#axis =0 is y, axis = -1 is x
        self.set_values(smooth_data)

    def smooth2(self,data,kernel_size = 40):#not as good
        kernel = np.ones(kernel_size) / kernel_size
        smooth_data = data#place holrder
        if self.direction == 'horizontal':#smooth in x direction
            for index, row in enumerate(data):
                smooth_data[index] = np.convolve(row, kernel, mode='same')
        elif self.direction == 'vertical':#smooth in y direction
            for i in range(0,len(data[0])):
                col=data[:,i]
                smooth_data[:,i] = np.convolve(col, kernel, mode='same')
        return smooth_data

    def set_values(self,smooth):
        dict = copy.deepcopy(self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index])
        dict['data'][:] = smooth.copy()
        self.figure.overview.data_handler.state_catalog.add_state(dict,'smooth' + self.direction)
        self.figure.update_colour_scale()

class Derivative_x(Raw):
    def __init__(self,figure):
        super().__init__(figure)

    def run2(self):#DOI: 10.1063/1.3585113
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

    def run(self):#numpy method
        if len(self.figure.int.shape) == 2:
            axis0 = 0
        else:
            axis0 = 1

        #1st derivatives in both directions
        data1_x = np.gradient(self.figure.int, axis=axis0 + 1)
        data1_y = np.gradient(self.figure.int, axis=axis0)

        # 2nd derivatives in both directions
        data2_x  = np.gradient(data1_x, axis=axis0+1)
        data2_y = np.gradient(data1_y, axis=axis0)

        self.set_values(data2_x,data2_y)

    def set_values(self,data2_x,data2_y):
        dict = copy.deepcopy(self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index])
        dict['data'][:] = data2_x.copy()
        self.figure.overview.data_handler.state_catalog.add_state(dict,'derivative_x')
        self.figure.update_colour_scale()

class Derivative_y(Derivative_x):
    def __init__(self,figure):
        super().__init__(figure)

    def set_values(self,data2_x,data2_y):
        dict = copy.deepcopy(self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index])
        dict['data'][:] = -data2_y.copy()
        self.figure.overview.data_handler.state_catalog.add_state(dict,'derivative_y')
        self.figure.update_colour_scale()

class Curvature_x(Raw):
    def __init__(self,figure):
        super().__init__(figure)

    def run(self):#numpy method
        if len(self.figure.int.shape) == 2:
            axis0 = 0
        else:
            axis0 = 1

        #1st derivatives in both directions
        data1_x = np.gradient(self.figure.int, axis=axis0+1)
        data1_y = np.gradient(self.figure.int, axis=axis0)

        # 2nd derivatives in both directions
        data2_x  = np.gradient(data1_x, axis=axis0+1)
        data2_y = np.gradient(data1_y, axis=axis0)

        self.set_values(data2_x,data2_y,data1_x,data1_y)

    def set_values(self,data2_x,data2_y,data1_x,data1_y):
        self.figure.int = data2_x/(1 + data1_x**2)**(1.5)#can change 1 to other values to optimise
        self.figure.redraw()

class Curvature_y(Curvature_x):
    def __init__(self,figure):
        super().__init__(figure)

    def set_values(self,data2_x,data2_y,data1_x,data1_y):
        self.figure.int = data2_y/(1 + data1_y**2)**(1.5)#can change 1 to other values to optimise
        self.figure.redraw()

class Convert_k(Raw):
    def __init__(self,figure):
        super().__init__(figure)
        self.hv = float(self.figure.overview.data_handler.file.get_data('metadata')['hv'])

    def run(self):#called when pressing the botton
        self.convert2k()
        self.figure.figure_handeler.update_mouse_range()

    def convert2k(self):
        work_func = 4#usually 4
        k0 = 0.5124 * np.sqrt(self.hv - work_func)
        #alpha is the polar or theta -> SIS
        #beta is the tilt -> SIS

        # Angle to radian conversion
        pos1 = self.figure.cursor.sta_horizontal_line.get_data()
        pos2 = self.figure.cursor.sta_vertical_line.get_data()
        dalpha,dbeta = -pos1[1],-pos2[0]#the offsets

        alpha,beta = self.figure.define_angle2k()#depends on the figure
        a = (alpha + dalpha)*np.pi/180
        b = (beta + dbeta)*np.pi/180

        # place hodlers
        nkx = len(alpha)
        nky = len(beta)
        KX = np.empty((nkx, nky))
        KY = np.empty((nkx, nky))

        if self.figure.overview.data_tab.data_loader.orientation == 'horizontal':
            for i in range(nkx):
                KX[i] = np.sin(b) * np.cos(a[i])
                KY[i] = np.sin(a[i])

        elif self.figure.overview.data_tab.data_loader.orientation == 'vertical':
            # Precalculate outside the loop
            theta_k = beta*np.pi/180
            cos_theta = np.cos(theta_k)
            sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta*np.pi/180)
            for i in range(nkx):
                KX[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * np.sin(dbeta*np.pi/180)
                KY[i] = cos_theta * np.sin(a[i])

        if KY.shape[1] == 1:#2D, band
            dict = self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index].copy()
            dict['yscale'] = np.linspace(k0*KY.min(), k0*KY.max(),len(KY.ravel()))#update
            self.figure.overview.data_handler.state_catalog.add_state(dict,'k_convert')
        else:#3D, FS
            self.new_mesh_all(k0*KX,k0*KY)

    def new_mesh_all(self,kx,ky):#make for every layer in one go: make a new mesh, apply the same changes to all layers
        min_index = [np.argmin((kx[:,-1]-kx[:,0])),np.argmin((ky[-1]-ky[0]))]#the index in whihc there is the minimum distance between the intensity mesh

        #min_distance = [kx[index[0]][1]-kx[index[0]][0], ky[1][index[1]]-ky[0][index[1]]]#minimum bin size
        min_bin = [(np.amax(kx[min_index[0]]) - np.amin(kx[min_index[0]]))/len(kx[min_index[0]]),(np.amax(ky[:,min_index[1]]) - np.amin(ky[:,min_index[1]]))/len(ky[:,min_index[1]])]#min bin size

        max_index = [np.argmax((kx[:,-1]-kx[:,0])),np.argmax((ky[-1]-ky[0]))]#the index in whihc there is the max distance betwene the intensitie mesh
        max_distance = [np.amax(kx[max_index[0]]) - np.amin(kx[max_index[0]]),np.amax(ky[:,max_index[1]]) - np.amin(ky[:,max_index[1]])]
        number = [max_distance[0]/min_bin[0],max_distance[1]/min_bin[1]]

        axis_y = np.linspace(np.amin(ky[:,max_index[1]]),np.amax(ky[:,max_index[1]]),num = int(number[1]))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_x =np.linspace(np.amin(kx[max_index[0]]),np.amax(kx[max_index[0]]),num = int(kx.shape[1]))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance

        #reshape the intensity: under the assumption that x-axis doen't shrink
        intensity = np.zeros((len(axis_y),len(axis_x),len(self.figure.data[2])))#place holder for mesh
        inrange = False#a flag to check if in range
        intensity[:] = np.NaN
        for col, x_cord in enumerate(axis_x):
            index_real = [0,0]#the index of the kspace coordinates
            for row,y_cord in enumerate(axis_y):#from below
                if y_cord < ky[index_real[1]][col]:#below
                    real_int = np.empty((1,len(self.figure.data[2])))[0]
                    real_int[:] = np.NaN
                    if inrange:
                        real_int = self.figure.data[3][:,index_real[1],col]
                elif y_cord > ky[-1][col]:#above
                    inrange = False
                    real_int = np.empty((1,len(self.figure.data[2])))[0]
                    real_int[:] = np.NaN
                else:#if bigger
                    real_int = self.figure.data[3][:,index_real[1],col]
                    index_real[1] += 1
                    inrange = True
                intensity[row][col][:] = real_int

        dict = self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index].copy()
        dict['yscale'] = axis_y
        dict['xscale'] = axis_x
        dict['data'] = np.transpose(intensity,(2, 0, 1))
        self.figure.overview.data_handler.state_catalog.add_state(dict,'k_convert')

class Convert_kz(Raw):
    def __init__(self,figure):
        super().__init__(figure)

    def run(self):
        self.converthv()

    def converthv(self):#convert to kz
        q = 1.60218*10**-19#charge
        m = 9.1093837*10**-31#kg
        hbar = (6.62607015*10**-34)/(2*np.pi)#m2 kg / s
        V = 8*q#J: inner potential
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

        # approximatly the number of division of each original cell, 2 approx 4 times more pixel
        division = 4

        self.create_rectangular_mesh(kz,ky, division ,m,hbar,V)



        #to let ppcolormesh handle the interpolation
        # dict = self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index].copy()
        # dict['xscale'] = kz
        # dict['yscale'] = ky
        # self.figure.overview.data_handler.state_catalog.add_state(dict,'k_convert')
        return

        #manually interpolate all layers so that cuts become easier
        #self.new_mesh_interpolation(kz,ky)




    def create_rectangular_mesh(self,kx,ky,division,m,hbar,V):
        kx = np.array(kx)
        ky = np.array(ky)




        axis_x =np.linspace(kx.min(),kx.max(),num = min(round(len(kx[0])*division),800))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance
        axis_y = np.linspace(ky.min(),ky.max(),num = min(round(len(kx)*division),800))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_z = np.linspace(self.figure.data[2].min(),self.figure.data[2].max(),num = len(self.figure.data[3]))



        value_position = np.full((axis_x.size,axis_y.size),-2)
        #check = np.full((len(kx),len(kx[0])),False)





        #we calculate the average theta of each ray of the data set
        theta = np.arctan(kx/ky)
        theta_line = np.array([])

        radius = np.sqrt(kx[:,0]**2+ky[:,0]**2)
        min_radius = np.average(radius)
        radius_end = np.sqrt(kx[:,-1]**2+ky[:,-1]**2)
        max_radius = np.average(radius_end)

        for i in range(len(kx)):
            theta_line = np.append(theta_line,np.average(theta[i]))



        array_length = len(kx[0])

#We check that the the new pixel is between the two exteral theta angle to know if it is on the data set, if yes we just search the minimum distance in the ray with the nearest angle of the pixel. This allow to pass from a complexity O(n**4) for a brut search to O(n**3) for this loop
        for i in range(len(axis_x)):
            for j in range(len(axis_y)):
                angle = np.arctan(axis_x[i]/axis_y[j])
                r = np.sqrt(axis_x[i]**2 + axis_y[j]**2)
                if abs(angle)>abs(theta_line[-1]) and abs(angle)>abs(theta_line[0]) and r>=min_radius and r<=max_radius:
                    ik = np.argmin(np.absolute(theta_line-angle))
                    distance = np.sqrt((kx[ik]-axis_x[i])**2+(ky[ik]-axis_y[j])**2)
                    jk = np.argmin(distance)
                    value_position[i,j] = ik*array_length+jk
                    #check[ik,jk] = True

        #to check if there is any data point that is not transmitted to the new grid
        # lost_count = 0
        # for i in range(len(kx)):
        #     for j in range(len(kx[0])):
        #         if not check[ik,jk]:
        #             lost_count = lost_count+1
        #
        # print(lost_count)

        Z = np.zeros((len(axis_x),len(axis_y),len(axis_z)))
        #points = np.column_stack((kx.flatten(),ky.flatten()))
        # for i in range(len(axis_x)):
        #     for j in range(len(axis_y)):
        #         #Ek = ((axis_x[i]**2+axis_y[j]**2)*hbar**2)/(2*m)*10**20-V
        #         #if
        #         d = (points-np.array([axis_x[i],axis_y[j]]))**2
        #         distance = np.sqrt(d[:,0]+d[:,1])
        #
        #         #print(distance[np.argmin(distance)])
        #
        #         if distance[np.argmin(distance)]<0.1:
        #             value_position[i,j] = np.argmin(distance)




        array_length = len(kx[0])

        for k in range(len(axis_z)):
            for i in range(len(axis_x)):
                for j in range(len(axis_y)):
                    if value_position[i,j]>-2:
                        ik,jk = value_position[i,j]//array_length,value_position[i,j]%array_length

                        Z[i,j,k] = self.figure.data[3][k,ik,jk]


        dict = self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index].copy()
        dict['xscale'] = axis_x
        dict['yscale'] = axis_y
        dict['zscale'] = axis_z
        dict['data'] = np.transpose(Z,(2, 1, 0))
        self.figure.overview.data_handler.state_catalog.add_state(dict,'k_convert')





















    def new_mesh_interpolation(self,kx,ky):
        min_index = [np.argmin(kx[:].max(axis=0)-kx[:].min(axis=0)),np.argmin(ky[:].max(axis=0)-ky[:].min(axis=0))]#the index in whihc there is the minimum distance between the intensity mesh

        length = np.argmax(kx[:,min_index[0]])-np.argmin(kx[:,min_index[0]])
        min_bin = [(np.amax(kx[:,min_index[0]]) - np.amin(kx[:,min_index[0]]))/length,(np.amax(ky[:,min_index[1]]) - np.amin(ky[:,min_index[1]]))/len(ky[:])]#min bin size

        #max_index = [np.argmax((kx[:,-1]-kx[:,0])),np.argmax((ky[-1]-ky[0]))]#the index in whihc there is the max distance betwene the intensitie mesh
        max_distance = [kx.max() - kx.min(),ky.max() - ky.min()]
        number = [max_distance[0]/min_bin[0],max_distance[1]/min_bin[1]]

        axis_y = np.linspace(ky.min(),ky.max(),num = min(round(number[1]),800))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_x =np.linspace(kx.min(),kx.max(),num = min(round(number[0]),800))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance
        axis_z = np.linspace(self.figure.data[2].min(),self.figure.data[2].max(),num = 800)

        X, Y = np.meshgrid(axis_x,axis_y)
        points = np.column_stack((kx.flatten(),ky.flatten()))
        Z = np.zeros((len(axis_x),len(axis_y),len(axis_z)))#place holder for mesh
        Z[:] = np.NaN
        for index, ev in enumerate(axis_z):
            interp = interpolate.LinearNDInterpolator(points,self.figure.data[3][index].flatten())
            Z[:,:,index] = interp(X,Y).T
            print(index/len(axis_z))

        dict = self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index].copy()
        dict['xscale'] = axis_x
        dict['yscale'] = axis_y
        dict['zscale'] = axis_z
        dict['data'] = np.transpose(Z,(2, 1, 0))
        self.figure.overview.data_handler.state_catalog.add_state(dict,'k_convert')

    def new_mesh_all(self,kx,ky):#manually interpolate each layer at once -> doesn't look perfect
        min_index = [np.argmin(kx[:].max(axis=0)-kx[:].min(axis=0)),np.argmin(ky[:].max(axis=0)-ky[:].min(axis=0))]#the index in whihc there is the minimum distance between the intensity mesh

        length = np.argmax(kx[:,min_index[0]])-np.argmin(kx[:,min_index[0]])
        min_bin = [(np.amax(kx[:,min_index[0]]) - np.amin(kx[:,min_index[0]]))/length,(np.amax(ky[:,min_index[1]]) - np.amin(ky[:,min_index[1]]))/len(ky[:])]#min bin size

        #max_index = [np.argmax((kx[:,-1]-kx[:,0])),np.argmax((ky[-1]-ky[0]))]#the index in whihc there is the max distance betwene the intensitie mesh
        max_distance = [kx.max() - kx.min(),ky.max() - ky.min()]
        number = [max_distance[0]/min_bin[0],max_distance[1]/min_bin[1]]

        axis_y = np.linspace(ky.min(),ky.max(),num = round(number[1]))#make a 1D array from the 2D ky with a lince spacing defined by the minimum distance
        axis_x =np.linspace(kx.min(),kx.max(),num = round(number[0]))#make a 1D array from the 2D kx with a lince spacing defined by the minimum distance

        #theoretical conversion
        q = 1.60218*10**-19#charge
        m = 9.1093837*10**-31#kg
        hbar = (6.62607015*10**-34)/(2*np.pi)#m2 kg / s
        V = 8*q#J
        W = 4.5#eV
        Eb = 0#eV binding energy
        ky_theory = []
        kz_theory = []
        theta = np.linspace(self.figure.data[1].min(),self.figure.data[1].max(),num=len(axis_y))
        hvs = np.linspace(self.figure.data[0].min(),self.figure.data[0].max(),num=len(axis_x))
        for hv in hvs:#do it for each photon energy
            Ek = (hv - W - Eb)*q#J -> can be extract the value from the figure?
            test = self.convert2k_2(hv,theta)[:,0]
            ky_theory.append(test)
            kz_theory.append(10**-10*np.sqrt(2*m*(Ek*np.cos(np.pi*theta/180)**2+V))/hbar)

        kz_theory = np.array(kz_theory)
        ky_theory = np.array(ky_theory)

        #the bounds
        left = [kz_theory[0],ky_theory[0]]
        right = [kz_theory[-1],ky_theory[-1]]
        bottom = [kz_theory[:,0],ky_theory[:,0]]
        top = [kz_theory[:,-1],ky_theory[:,-1]]

        #plt.plot(kz_theory[0],ky_theory[0])
        #plt.plot(kz_theory[-1],ky_theory[-1])
        #plt.plot(kz_theory[:,0],ky_theory[:,0])
        #plt.plot(kz_theory[:,-1],ky_theory[:,-1])
        #plt.show()

        print("let's fill")
        new_data = np.zeros((len(axis_y),len(axis_x),len(self.figure.data[2])))#place holder for mesh
        new_data[:] = np.NaN
        for col, x_cord in enumerate(axis_x):
            for row, y_cord in enumerate(axis_y):
                if y_cord >= bottom[1][col] and y_cord <= top[1][col] :#are we above the bottom line and below the top line?
                    if x_cord >= left[0][row] and x_cord <= right[0][row]:#are we right of the left boundary? #and are we left of the right boundary?#and y_cord <= left[1][row] # and y_cord >= right[1][row]
                        #interpolation
                        diff_y = np.abs(ky - y_cord)
                        index_y = np.unravel_index(diff_y.argmin(), diff_y.shape)
                        diff_x = np.abs(kx[index_y[0]] - x_cord)
                        index_x = np.unravel_index(diff_x.argmin(), diff_x.shape)

                        intensity = self.figure.data[3][:,index_y[0],index_x][:,0]

                    else:#if ourside
                        intensity = np.empty((1,len(self.figure.data[2])))[0]
                        intensity[:] = 0#np.NaN

                else:#not above or below the top liens
                    intensity = np.empty((1,len(self.figure.data[2])))[0]
                    intensity[:] = 0#np.NaN

                new_data[row][col][:] = intensity

        self.figure.data[3] = np.transpose(new_data,(2, 0, 1))
        self.figure.data[0] = axis_x
        self.figure.data[1] = axis_y
        self.figure.intensity()

    def convert2k_2(self,hv,theta):#for the theory
        work_func = 4#usually 4
        hv = hv#incident energy
        k0 = 0.5124 * np.sqrt(hv - work_func)

        #alpha is the polar or theta
        #beta is the tilt

        # Angle to radian conversion
        pos1 = self.figure.cursor.sta_horizontal_line.get_data()
        pos2 = self.figure.cursor.sta_vertical_line.get_data()

        dalpha,dbeta = -pos1[1],-pos2[0]#the offsets
        alpha,beta = theta, np.array([self.figure.tilt])
        a = (alpha+dalpha)*np.pi/180
        b = (beta+dbeta)*np.pi/180

        # place hodlers
        nkx = len(alpha)
        nky = len(beta)
        KX = np.empty((nkx, nky))
        KY = np.empty((nkx, nky))

        if self.figure.overview.data_tab.data_loader.orientation == 'horizontal':
            for i in range(nkx):
                KX[i] = np.sin(b) * np.cos(a[i])
                KY[i] = np.sin(a[i])

        if self.figure.overview.data_tab.data_loader.orientation == 'vertical':
            # Precalculate outside the loop
            theta_k = beta*np.pi/180
            cos_theta = np.cos(theta_k)
            sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta*np.pi/180)
            for i in range(nkx):
                KX[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * \
                        np.sin(dbeta*np.pi/180)
                KY[i] = cos_theta * np.sin(a[i])

        return k0*KY

    def convert2k(self,hv):
        work_func = 4#usually 4
        hv = hv#incident energy
        k0 = 0.5124 * np.sqrt(hv - work_func)

        #alpha is the polar or theta
        #beta is the tilt

        # Angle to radian conversion
        pos1 = self.figure.cursor.sta_horizontal_line.get_data()
        pos2 = self.figure.cursor.sta_vertical_line.get_data()

        dalpha,dbeta = -pos1[1],-pos2[0]#the offsets
        alpha,beta = self.figure.define_hv()#depends on the figure
        a = (alpha + dalpha)*np.pi/180
        b = (beta + dbeta)*np.pi/180

        # place hodlers
        nkx = len(alpha)
        nky = len(beta)
        KX = np.empty((nkx, nky))
        KY = np.empty((nkx, nky))

        if self.figure.overview.data_tab.data_loader.orientation == 'horizontal':
            for i in range(nkx):
                KX[i] = np.sin(b) * np.cos(a[i])
                KY[i] = np.sin(a[i])

        if self.figure.overview.data_tab.data_loader.orientation == 'vertical':
            # Precalculate outside the loop
            theta_k = beta*np.pi/180
            cos_theta = np.cos(theta_k)
            sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta*np.pi/180)
            for i in range(nkx):
                KX[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * \
                        np.sin(dbeta*np.pi/180)
                KY[i] = cos_theta * np.sin(a[i])

        return k0*KY

class Fermi_level_band(Raw):#only the main figure
    def __init__(self,parent_figure):
        super().__init__(parent_figure)
        ref_data, gold = self.figure.overview.data_tab.data_loader.gold_please()
        self.gold_file = gold
        self.gold = ref_data
        self.kB = 1.38064852e-23 #[J/K]
        self.eV = 1.6021766208e-19#[J]
        self.W = 4.38#work function [eV]
        self.hv = float(self.figure.overview.data_handler.file.get_data('metadata')['hv'])
        self.e_0 = self.hv - self.W#initial guess of fermi level
        self.T = 10#K the temperature

    def run(self):
        self.fit()#kevins stuff
        self.fit_polynomal()#make EF smooth with poly fit
        self.pixel_shift()#shift the data so that we get a rectangle data grid
        self.update_figure()

    def update_figure(self):
        self.figure.figure_handeler.update_mouse_range()

    def fit_polynomal(self):
        polynomal = np.polyfit(self.pos, self.EF,4)
        xp = self.figure.data[1]
        p = np.poly1d(polynomal)
        self.EF = p(xp)

        #start_index = 0
        #end_index = len(self.gold[0]['data'][0])
        #self.EF[0:start_index] = self.EF[start_index]
        #self.EF[end_index:-1] = self.EF[end_index]

    def pixel_shift(self):#pixel ashift and add NaN such that the index of the fermilevel allign along x in the data
        print('lets shift')
        energies = self.figure.data[0]
        fermi_levels = self.EF
        fermi_index = np.array([np.argmin(np.abs(energies - f)) for f in fermi_levels],dtype=int)

        max_shift = max(fermi_index)-min(fermi_index)
        new_data = np.array([energies - level for level in fermi_levels])#shifted data#s
        target_index = max(fermi_index)

        dE = energies[1] - energies[0]

        new_array = np.zeros((len(fermi_levels),len(new_data[0])+max_shift))#place holder
        new_intensity = np.zeros((len(fermi_levels),len(new_data[0])+max_shift))#place holder
        new_intensity[:] =  0
        intensity = self.figure.int

        for row, array in enumerate(new_data):
            shift = target_index - fermi_index[row]
            if shift != 0:#insert at the begnning
                empty_1 = np.empty(shift)
                empty_1[:] = array[0]
                array = np.insert(array,0,empty_1)
                empty_1[:] = 0
                temp = np.insert(intensity[row],0,empty_1)
            else:
                temp = intensity[row]

            #insert at the end
            more_shift = max_shift - shift
            empty_1 = np.empty(more_shift)
            empty_1[:] = array[-1]
            array = np.append(array,empty_1)
            empty_1[:] = 0
            temp = np.append(temp,empty_1)

            new_array[row] = array
            new_intensity[row] = temp

        new_axis = np.linspace(new_array.min(), new_array.max(),len(new_intensity[0,:]))

        dict = copy.deepcopy(self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index])
        dict['xscale'] = new_axis
        if self.figure.overview.operations.fermi_normalisation.configure('text')[-1] == 'on':
            new_intensity = self.normalise(new_intensity)
        dict['data'] = np.transpose(np.atleast_3d(new_intensity),(2,0,1))
        idx = self.gold_file.rfind('/') + 1
        name = self.gold_file[idx:]
        self.figure.overview.data_handler.state_catalog.add_state(dict,'fermilevel_'+self.figure.overview.operations.fermi_normalisation.configure('text')[-1] + ':_' + name)

    def normalise(self,new_intensity):
        difference_array = np.absolute(self.gold[0]['xscale'] - self.EF.min())#subtract for each channel, works.
        index1 = np.argmin(difference_array)
        int = self.gold[0]['data'][0][:,0:index1]/len(self.gold[0]['xscale'][0:index1])#shod it star tfrom 0? should we corect the EF for this as well? probablu slow tohugh
        total_MDC = np.nansum(int,axis=1)#of gold
        return (new_intensity.T/total_MDC).T#works for 2D

    def fit(self):
        gold = self.gold[0]['data'][0]
        n_pixels, n_energies = gold.shape
        energies = self.gold[0]['xscale']

        params = []
        functions = []
        int_range = 0
        self.pos = []#y position of the EDCs

        for i in range(0, len(gold), 20):
            #edc = gold[i]
            start,stop=max(i-int_range,0),i+1+int_range
            step = stop - start
            edc = sum(gold[start:stop:1])/step


        #for i, edc in enumerate(gold):
            if i >= 0:#temp fix, for FS fits in PrAlGe.
                self.pos.append(self.figure.data[1][start])
                lenght = int(len(edc)*0)
                p, res_func = self.fit_fermi_dirac(energies[lenght:-1], edc[lenght:-1], self.e_0, T=self.T)
                params.append(p)
                self.e_0 = p[0]#update teh guess
                functions.append(res_func)
            else:
                p = [23.6,0,0,0]
                res_func = None
                params.append(p)
                self.e_0 = p[0]#update teh guess

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
        kT = self.kB * self.T / self.eV
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

        new_intensity = np.array(new_intensity)
        new_axis = np.linspace(new_array.min(), new_array.max(),len(new_intensity[0,:,0]))

        dict = self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index].copy()
        dict['zscale'] = new_axis
        if self.figure.overview.operations.fermi_normalisation.configure('text')[-1] == 'on':
            new_intensity = self.normalise(new_intensity)
        dict['data'] = new_intensity#np.transpose(new_intensity, (1, 0, 2))
        self.figure.overview.data_handler.state_catalog.add_state(dict,'fermilevel')

    def normalise(self,new_intensity):
        difference_array = np.absolute(self.gold[0]['xscale'] - self.EF.min())#subtract for each channel, works.
        index1 = np.argmin(difference_array)
        int = self.gold[0]['data'][0][:,0:index1]/len(self.gold[0]['xscale'][0:index1])#shod it star tfrom 0? should we corect the EF for this as well? probablu slow tohugh
        total_MDC = np.nansum(int,axis=1)#of gold
        result = np.transpose(new_intensity,(1,0,2))/total_MDC[:,np.newaxis]
        return result

class EF_corr_3D(Raw):#only the main figure
    def __init__(self,parent_figure):
        super().__init__(parent_figure)
        self.kB = 1.38064852e-23 #[J/K]
        self.eV = 1.6021766208e-19#[J]
        self.W = 4.38#work function [eV]
        self.hv = float(self.figure.overview.data_handler.file.get_data('metadata')['hv'])
        self.e_0 = self.hv - self.W#initial guess of fermi level
        self.T = 10#K the temperature

    def run(self):
        self.fit()#kevins stuff
        self.update_figure()

    def update_figure(self):
        self.figure.figure_handeler.update_mouse_range()

    def pixel_shift(self,cut):#pixel ashift and add NaN such that the index of the fermilevel allign along x in the data
        print('lets shift')
        energies = self.figure.data[2]

        fermi_levels = self.EF
        fermi_index = np.array([np.argmin(np.abs(energies - f)) for f in fermi_levels],dtype=int)#look for 0
        max_shift = max(fermi_index)-min(fermi_index)
        new_data = np.array([energies - level for level in fermi_levels])#shifted data#s
        target_index = max(fermi_index)

        dE = energies[1] - energies[0]

        new_array = np.zeros((len(fermi_levels),len(new_data[0])+max_shift))#place holder
        new_intensity = np.zeros((len(fermi_levels),len(new_data[0])+max_shift))#place holder
        new_intensity[:] =  np.nan
        intensity = cut

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
        return new_intensity, new_axis

    def fit(self):
        data = self.figure.data[-1]
        energies = self.figure.data[2]

        new_intensity=[]
        temp = np.transpose(self.figure.data[3])
        clip_radius = float(self.figure.overview.operations.c_clip_entry.get())

        for i in range(0,len(self.figure.data[0])):
            params = []
            self.pos = []
            cut = temp[i,:,:]
            self.e_0 = self.hv - self.W#initial guess of fermi level
            int_range = 0

            #look for index within the defined circle
            x = self.figure.data[0][i]
            y = (clip_radius**2 - x**2)**0.5

            self.start_index = np.argmin(np.abs(self.figure.data[1] + y))
            self.end_index = np.argmin(np.abs(self.figure.data[1] - y))

            for i in range(self.start_index, self.end_index, 20):
                start,stop=i-int_range,i+1+int_range
                step = stop- start
                edc = sum(cut[start:stop:1])/step
                self.pos.append(self.figure.data[1][start])
                lenght = int(len(cut)*0.14)
                p, cov = self.fit_fermi_dirac(energies[lenght:-1], edc[lenght:-1], self.e_0, T = self.T)
                params.append(p)
                self.e_0 = p[0]#update the guess

            # Prepare the results
            params = np.array(params)
            fermi_levels = params[:,0]
            sigmas = params[:,1]
            slopes = params[:,2]
            offsets = params[:,3]

            self.EF = fermi_levels#need to fit a polynomal to make a continuis Efs
            self.fit_polynomal()
            #plt.pcolormesh(self.figure.data[2],self.figure.data[1],cut)
            #plt.plot(self.EF,self.figure.data[1])
            #plt.show()
            intensity, axis = self.pixel_shift(cut)
            new_intensity.append(np.transpose(intensity))

        corr_intensity = self.correct_intensity(new_intensity)
        dict = self.figure.overview.data_handler.file.data[self.figure.overview.data_handler.file.index].copy()
        dict['zscale'] = np.linspace(axis.min(),axis.max(),len(corr_intensity))
        dict['data'] = corr_intensity
        self.figure.overview.data_handler.state_catalog.add_state(dict,'fermi_corr')

    def correct_intensity(self,new_intensity):
        maxList = max(new_intensity, key = len)
        maxLength = len(maxList)
        placeholder = np.zeros((maxLength,len(self.figure.data[1]),len(self.figure.data[0])))
        placeholder[:] = np.nan
        for index, intensity in enumerate(new_intensity):
            start_index = 0
            placeholder[start_index:len(intensity),start_index:len(np.transpose(intensity)),index] = intensity
        return placeholder

    def fit_polynomal(self):
        polynomal = np.polyfit(self.pos, self.EF,4)
        xp = self.figure.data[1]
        p = np.poly1d(polynomal)
        self.EF = p(xp)

        self.EF[0:self.start_index] = self.EF[self.start_index]
        self.EF[self.end_index:-1] = self.EF[self.end_index]

    def fit_fermi_dirac(self,energies,edc,e_0, T=10, sigma0=1, a0=0, b0=-0.1):
        # Normalize the EDC to interval [0, 1]
        edcmin = edc.min()
        edcmax = edc.max()
        edc = (edc-edcmin)/max((edcmax-edcmin),1)

        # Initial guess and bounds for parameters
        p0 = [e_0, sigma0, a0, b0]
        de = 1
        lower = [e_0-de, 0, -10, -1]
        upper = [e_0+de, 100, 10, 1]

        # Carry out the fit
        p, cov = curve_fit(self.FD_function, energies, edc, p0=p0, bounds=(lower, upper))

        return p, cov

    def FD_function(self,E, E_F, sigma, a, b, T=10):
        # Basic Fermi Dirac distribution at given T
        kT = self.kB * self.T / self.eV
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

class Range_plot(Raw):
    def __init__(self,parent_figure):
        super().__init__(parent_figure)
        self.slide_limits = [0,5]
        self.define_slide()
        self.define_entry()
        pos = [300,0]
        self.fig = figure.DOS_down(self.figure.overview,pos)

    def define_slide(self):
        self.scale = tk.Scale(self.figure.overview.tab,from_=self.slide_limits[0],to=self.slide_limits[1],orient=tk.HORIZONTAL,command=self.update_range,resolution=1)
        self.scale.pack()

    def update_range(self,value):
        range = (self.figure.ylimits[1]-self.figure.ylimits[0])*(1/self.slide_limits[1])*0.5
        self.figure.overview.range = int(value)*range
        self.figure.cursor.draw_sta_line()

    def define_mouse(self):
        self.figure.cursor = cursor.Range_cursor(self.figure)
        self.figure.canvas.get_tk_widget().bind( "<Motion>", self.figure.cursor.on_mouse_move)#move
        self.figure.canvas.get_tk_widget().bind( "<B1-Motion>", self.figure.cursor.drag)#left click

    def define_entry(self):
        self.e1 = tk.Entry(self.figure.overview.tab,width=5)#the step size
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

class Symmetrise(Raw):
    def __init__(self,parent_figure):
        super().__init__(parent_figure)

    def run(self):
        self.symmetrise()
        self.update_figure()

    def symmetrise(self):
        intensity = self.figure.int

        half_intensity = np.flip(intensity[:,0:int(0.5*len(intensity[0]))])
        intensity[:,int(0.5*len(intensity[0])):-1] = half_intensity

        self.figure.int = intensity

    def update_figure(self):
        self.figure.figure_handeler.update_sort_data()#update the cuts, but avoid for main figure
        #self.figure.figure_handeler.update_intensity()
        self.figure.figure_handeler.draw()
        self.figure.figure_handeler.update_mouse_range()
