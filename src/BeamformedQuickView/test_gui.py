
# The UI interface and analysis of the lofar solar beam from

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.uic import loadUi
from pylab import get_current_fig_manager
import matplotlib
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import readsav
from scipy.interpolate import griddata
from skimage import measure
import datetime
import matplotlib.dates as mdates


matplotlib.use('TkAgg')

class MatplotlibWidget(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)

        loadUi("layout.ui", self)

        self.move(10,30)
        self.init_graph()
        self.setWindowIcon(QIcon("resource/lofar.png"))
        self.addToolBar(NavigationToolbar(self.mplw.canvas, self))
        self.dataset = LofarData()

        self.asecpix = 15

        self.x_select = 0
        self.y_select = 0
        self.selected = False
        self.interpset = 'cubic'

        self.interp_nearest.setChecked(False)
        self.interp_linear.setChecked(False)
        self.interp_cubic.setChecked(True)

        self.show_disk.setChecked(True)
        self.show_FWHM.setChecked(True)
        self.show_peak.setChecked(True)

        self.action_prefix = '<span style=\" font-size:12pt; font-weight:600; color:#18B608;\" >[Action] </span>'
        self.info_prefix = '<span style=\" font-size:12pt; font-weight:600; color:#0424AE;\" >[Info] </span>'

        # define all the actions
        self.button_gen.clicked.connect(self.showBeamForm)
        self.pointing.clicked.connect(self.showPointing)
        self.loadsav.triggered.connect(self.update_lofarBF)

        self.interp_nearest.toggled.connect(lambda:self.btnstate(self.interp_nearest))
        self.interp_linear.toggled.connect(lambda:self.btnstate(self.interp_linear))
        self.interp_cubic.toggled.connect(lambda:self.btnstate(self.interp_cubic))


    def btnstate(self,b):
        self.interpset = (b.text().lower())

    def init_graph(self):

        self.mplw.canvas.axes.clear()
        self.mplw.canvas.axes.imshow(plt.imread('resource/login.png'))
        self.mplw.canvas.axes.set_axis_off()
        self.mplw.canvas.draw()

    def update_lofarBF(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()",
                                                  "","All Files (*);;Python Files (*.py)",
                                                  options=options)
        if fileName:
            print(fileName)

        self.dataset.load_sav(fileName)

        self.mplw.canvas.axes.clear()

        data_beam = self.dataset.data_cube[0, 0, :]
        x = np.linspace(-3000, 3000, 400)
        y = np.linspace(-3000, 3000, 400)
        X, Y = np.meshgrid(x, y)
        method = 'nearest'  # 'cubic'
        data_ds = self.dataset.data_cube[:, :, 0]
        self.mplw.canvas.axes.imshow(data_ds, aspect='auto', origin='lower',
                  vmin=(np.mean(data_ds) - 2 * np.std(data_ds)),
                  vmax=(np.mean(data_ds) + 3 * np.std(data_ds)),
                  extent=[self.dataset.time_ds[0], self.dataset.time_ds[-1],
                          self.dataset.freqs_ds[0], self.dataset.freqs_ds[-1]], cmap='inferno')
        self.mplw.canvas.axes.xaxis_date()
        self.mplw.canvas.axes.set_xlabel('Time (UT)')
        self.mplw.canvas.axes.set_ylabel('Frequency (MHz)')
        self.mplw.canvas.axes.set_title('LOFAR Beamform Observation ' + mdates.num2date(self.dataset.time_ds[0]).strftime('%Y/%m/%d'))
        for tick in self.mplw.canvas.axes.get_xticklabels():
            tick.set_rotation(25)
        self.mplw.canvas.axes.set_position([0.1,0.15,0.85,0.8])
        self.mplw.canvas.draw()

        self.mplw.canvas.mpl_connect('button_release_event', self.onclick)
        action_prefix = "<span style=\" font-size:12pt; font-weight:600; color:#18B608;\" >[Action] </span>"
        self.log.append(self.action_prefix+'Load : '+fileName)

    def onclick(self,event):
        if ~event.dblclick and event.button==1:

            print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
                  ('double' if event.dblclick else 'single', event.button,
                   event.x, event.y, event.xdata, event.ydata))
            self.x_select = event.xdata
            self.y_select = event.ydata
            self.input_t.setText(mdates.num2date(self.x_select).strftime('%H:%M:%S.%f'))
            self.input_f.setText('{:06.3f}'.format(self.y_select))
            self.t_idx_select =  (np.abs(self.dataset.time_ds  - self.x_select)).argmin()
            self.f_idx_select =  (np.abs(self.dataset.freqs_ds - self.y_select)).argmin()

            if self.selected:
                self.mplw.canvas.axes.lines.remove(self.mplw.canvas.axes.lines[0])
            self.mplw.canvas.axes.plot(self.x_select, self.y_select, 'w+', markersize=25, linewidth=2)
            self.mplw.canvas.draw()
            self.selected = True
            if plt.fignum_exists(4):
                self.showBeamForm()

    def showPointing(self):
        if self.dataset.havedata:
            plt.figure(5)
            plt.get_current_fig_manager().window.wm_geometry("+1150+550")
            plt.plot(self.dataset.xb,self.dataset.yb,'kx')
            ax = plt.gca()
            ax.set_xlabel('X (Arcsec)')
            ax.set_ylabel('Y (Arcsec)')
            ax.set_aspect('equal', 'box')

            plt.show()

    def showBeamForm(self):
        print(self.selected)
        if not self.selected:
            QMessageBox.about(self, "Attention", "Select a time-frequency point!")
        elif self.dataset.havedata:
            data_beam=self.dataset.data_cube[self.f_idx_select,self.t_idx_select,:]
            x = np.arange(-3000, 3000, self.asecpix)
            y = np.arange(-3000, 3000, self.asecpix)
            X, Y = np.meshgrid(x, y)
            method = self.interpset
            data_bf = griddata((self.dataset.xb, self.dataset.yb), data_beam,
                               (X, Y), method=method, fill_value=np.min(data_beam))

            self.log.append(self.action_prefix+' Beam Form at'+
                            mdates.num2date(self.x_select).strftime('%H:%M:%S.%f') +' of '
                            '{:06.3f}'.format(self.y_select)+'MHz')

            fig = plt.figure(4)
            plt.get_current_fig_manager().window.wm_geometry("+1150+50")
            #fig.canvas.manager.window.move(1200, 70)

            fig.clear()
            ax = plt.gca()
            im = ax.imshow(data_bf, cmap='hot',
                      origin='lower',extent=[np.min(X),np.max(X),np.min(Y),np.max(Y)])
            ax.set_xlabel('X (Arcsec)')
            ax.set_ylabel('Y (Arcsec)')
            ax.set_aspect('equal', 'box')
            plt.colorbar(im)
            print(np.min(data_bf)+(np.max(data_bf)-np.min(data_bf))/2.0)
            if self.show_FWHM.isChecked():
                ax.contour(X,Y,data_bf,levels=[np.min(data_bf)+(np.max(data_bf)-np.min(data_bf))/2.0],colors=['deepskyblue'])

            FWHM_thresh = np.min(data_bf)+(np.max(data_bf)-np.min(data_bf))/2.0
            img_bi = data_bf > FWHM_thresh
            bw_lb = measure.label(img_bi)
            rg_lb = measure.regionprops(bw_lb)
            x_peak = X[np.where(data_bf == np.max(data_bf))]
            y_peak = Y[np.where(data_bf == np.max(data_bf))]
            rg_id = bw_lb[np.where(data_bf == np.max(data_bf))]
            area_peak = rg_lb[int(rg_id)-1].area

            self.log.append(self.info_prefix+' [XY_peak:('+
                            '{:7.1f}'.format(x_peak[0])+','+
                            '{:7.1f}'.format(y_peak[0])+') asec] '+
                            '[Area:('+'{:7.1f}'.format(area_peak*(self.asecpix/60)**2)+
                            ') amin2]')

            if self.show_FWHM.isChecked():
                ax.contour(X,Y,np.abs(bw_lb-rg_id)<0.1,levels=[0.5],colors=['lime'])

            if self.show_disk.isChecked():
                ax.plot(960*np.sin(np.arange(0,2*np.pi,0.001)),
                        960*np.cos(np.arange(0,2*np.pi,0.001)),'w')

            if self.show_peak.isChecked():
                ax.plot(x_peak,y_peak,'k+')

            plt.show()

class LofarData:
    def __init__(self):
        self.fname = ''
        self.havedata = False

        self.title = ''
        self.data_cube = 0
        self.freqs_ds = 0
        self.time_ds = 0
        self.xb = 0
        self.yb = 0

    def load_sav(self, fname):
        self.fname = fname
        self.havedata = True

        data = readsav(fname, python_dict=True)

        self.title = data['ds'][0]['TITLE']
        self.data_cube = data['ds'][0]['CUBE']
        self.freqs_ds = data['ds'][0]['FREQS']
        self.time_ds = (data['ds'][0]['TIME']) / 3600 / 24 + mdates.date2num(datetime.datetime(1979, 1, 1))
        self.xb = data['ds'][0]['XB']
        self.yb = data['ds'][0]['YB']


app = QApplication([])
window = MatplotlibWidget()
window.show()
app.exec_()

