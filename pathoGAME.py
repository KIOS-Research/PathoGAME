# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PathoGAME
                                 A QGIS plugin
                              -------------------
        begin                : September 2022
        copyright            : (C) 2022 by KIOS Research and Innovation Center of Excellence (KIOS CoE)
        email                : kiriakou.marios@ucy.ac.cy
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QTimer, QRegExp
from qgis.PyQt.QtGui import QIcon, QFont, QRegExpValidator, QPixmap, QColor
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QTableWidgetItem
# Initialize Qt resources from file resources.py
from .resources import *

from qgis.core import QgsVectorLayer, QgsProject, QgsLayerTreeLayer, QgsFeatureRequest, QgsExpression, \
    QgsCoordinateReferenceSystem, QgsMapLayerType, QgsFeature
from PyQt5 import uic
import base64
# Import the code for the DockWidget
from .pathoGAME_dockwidget import pathoGAMEDockWidget
import os.path
import random
import numpy as np
from .MouseClick import MouseClick
from urllib.request import urlopen
import json
import operator
import subprocess
try:
    from epyt import epanet
except:
    subprocess.call(['pip', 'install', 'epyt'])


class pathoGAME:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.heart_choices = []
        self.type_files = []
        self.clickPhotos = None
        self.toolMouseClick = None
        self.level_index = None
        self.user_choice = ''
        self.user_station_choices = []
        self.time_left_int = None
        self.username = ''
        self.ri = None
        self.layers = None
        self.falld = None
        self.temp_location = None
        self.active_station = None
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'pathoGAME_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&pathoGAME')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'pathoGAME')
        self.toolbar.setObjectName(u'pathoGAME')

        # print "** INITIALIZING pathoGAME"

        self.pluginIsActive = False
        self.dockwidget = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('pathoGAME', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            checkable=False,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        if checkable:
            action.setCheckable(checkable)

        self.actions.append(action)

        return action

    def enable_menu_bar(self):
        if self.iface.mainWindow().menuBar().isVisible():
            self.iface.mainWindow().menuBar().setVisible(False)
        else:
            self.iface.mainWindow().menuBar().setVisible(True)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/pathoGAME/icons/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/pathoGAME/icons/icon_mouse.png'
        self.clickPhotos = self.add_action(
            icon_path,
            checkable=False,
            text=self.tr('Select junction to find the contamination location.'),
            callback=self.setMouseClickMapTool,
            parent=self.iface.mainWindow())

        # enable_menu_bar = self.add_action(
        #     icon_path,
        #     checkable=False,
        #     text=self.tr('On/Off Menubar of QGIS.'),
        #     callback=self.enable_menu_bar,
        #     parent=self.iface.mainWindow())

        self.toolMouseClick = MouseClick(self.canvas, self)
        self.iface.mapCanvas().setMapTool(self.toolMouseClick)

    # --------------------------------------------------------------------------

    def setMouseClickMapTool(self):
        self.iface.mapCanvas().setMapTool(self.toolMouseClick)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # print "** CLOSING pathoGAME"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        # print "** UNLOAD pathoGAME"
        self.clear_project()

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&pathoGAME'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # --------------------------------------------------------------------------

    def showMessage(self, title, msg, button, icon, fontsize=9):
        msgBox = QMessageBox()
        if icon == 'Warning':
            msgBox.setIcon(QMessageBox.Warning)
        if icon == 'Info':
            msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowTitle(title)
        msgBox.setText(msg)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.setStyleSheet("background-color: rgb(255, 255, 127);")
        font = QFont()
        font.setPointSize(fontsize)
        msgBox.setFont(font)
        msgBox.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        buttonY = msgBox.button(QMessageBox.Ok)
        buttonY.setText(button)
        buttonY.setFont(font)
        msgBox.exec_()

    def secs_to_minsec(self, secs):
        mins = secs // 60
        secs = secs % 60
        minsec = f'{mins:02}:{secs:02}'
        return minsec

    def update_sensor_detect(self):
        # print('sensors')
        # print(self.sensors_bydetection)
        if not self.sensors_bydetection:
            self.detect_time.stop()
            self.iface.messageBar().pushMessage("PathoGAME", f"Sensors cannot detect contamination. Please use the "
                                                             f"heart button.", level=1, duration=6)
            return

        if self.sensors_cnt == len(self.sensors_bydetection) - 1:
            self.detect_time.stop()

        # Add sensors
        try:
            self.junlyr.startEditing()
            sens = self.sensors_bydetection[self.sensors_cnt]
            sens = self.d.getNodeNameID(sens)
            expr = QgsExpression("\"id\"='" + sens + "'")
            it = self.junlyr.getFeatures(QgsFeatureRequest(expr))
            for feature in it:
                sel = feature
                break

            self.iface.messageBar().pushMessage("PathoGAME", f"Sensor detection at Junction {sel.id()}",
                                                level=0, duration=2)

            self.junlyr.changeAttributeValue(sel.id(), sel.fieldNameIndex('desc'), 'DETECT')
            self.junlyr.reload()
            self.junlyr.triggerRepaint()
            self.junlyr.commitChanges()
        except:
            pass

        self.sensors_cnt += 1

    def update_time(self):

        if self.show_answer == 0:
            self.time_left_int -= 1

        if self.time_left_int == 0:
            self.submit_game()
            self.time_game.stop()
            self.detect_time.stop()
            self.dockwidget.timer_lbl.setText(str('00:00'))
            return

        if (self.time_left_int % 40) < 10:
            self.dockwidget.timer_lbl.setStyleSheet("background-color: red")
        else:
            self.dockwidget.timer_lbl.setStyleSheet("background-color: #dfdfdf")

        if (self.time_left_int % 40) == 0:
            if self.show_answer == 0:
                self.iface.messageBar().pushMessage("PathoGAME", f"The location of the contaminant at level {str(self.level_index)} show "
                                          f"in orange color on map.", level=0, duration=2)
            try:
                QgsProject.instance().removeMapLayer(self.temp_location)
            except:
                pass
            self.temp_location = QgsVectorLayer("Point?crs=epsg:4326", "LOCATION", "memory")
            self.temp_location.loadNamedStyle(os.path.join(self.plugin_dir, "qmls", f'location.qml'))
            root = QgsProject.instance().layerTreeRoot()
            g = root.findGroup(f"Level {str(self.level_index)}")
            self.insert_layer_in_group(g, self.temp_location, True)

            for feature_loc in self.junlyr.getFeatures():
                if feature_loc['id'] == self.location_contaminant[self.level_index-1]:
                    contaminant_feature = feature_loc
                    feat = QgsFeature()
                    # for elem in layer.getFeatures():
                    feat.setGeometry(contaminant_feature.geometry())
                    self.temp_location.startEditing()
                    self.temp_location.addFeatures([feat])
                    self.temp_location.commitChanges()
                    break
            try:
                self.temp_location.reload()
                self.temp_location.triggerRepaint()
            except:
                pass

            self.show_answer += 1
            if self.level_index == 1:
                self.time_left_int = 80
            elif self.level_index == 2:
                self.time_left_int = 40

            self.detect_time.stop()
            self.iface.messageBar().clearWidgets()

            if self.show_answer == 5:

                try:
                    QgsProject.instance().layerTreeRoot().findGroup(
                        f"Level {str(self.level_index)}").setItemVisibilityChecked(
                        False)
                except:
                    pass

                self.level_index += 1

                self.user_station_choices.append(self.user_choice)
                self.user_score_total = self.user_score_total + self.user_score

                try:
                    self.next_station()
                except:
                    pass
                self.show_answer = 0

        minsec = self.secs_to_minsec(self.time_left_int)
        self.dockwidget.timer_lbl.setText(str(minsec))

    def insert_layer_in_group(self, g, layer, status):

        QgsProject.instance().addMapLayer(layer, False)
        g.setExpanded(status)
        nn = QgsLayerTreeLayer(layer)
        g.insertChildNode(0, nn)

    def give_username(self):
        self.dlg_user = uic.loadUi(os.path.join(self.plugin_dir, 'ui/start_game.ui'))
        regex = QRegExp("[a-z-A-Z_]+[0-9]+")
        validator = QRegExpValidator(regex)
        self.dlg_user.username.setValidator(validator)
        self.dlg_user.show()
        result = self.dlg_user.exec_()

        if result:
            # update username text.
            self.username = self.dlg_user.username.text()
            if self.username == '':
                self.showMessage("PathoGAME", "Please write a new username.", "OK", "Warning")
                return

            self.dockwidget.username_lbl.setText(self.username)
            self.start_game()

    def start_game(self):
        """ Start PathoCert game"""
        # clear project
        try:
            self.time_game.stop()
            self.detect_time.stop()
        except Exception as e:
            pass

        try:
            root = QgsProject.instance().layerTreeRoot()
            for level in range(0, 6):
                g = root.findGroup(f"Level {str(level)}")
                root.removeChildNode(g)

            g1 = root.findGroup(f"Anytown")
            root.removeChildNode(g1)

        except Exception as e:
            print(e)

        self.setMouseClickMapTool()
        self.dockwidget.heart1_btn.setEnabled(True)

        self.user_station_choices = []
        self.user_choice = ''
        self.level_index = 1
        self.active_station = ''
        self.selected_stations = []
        self.location_contaminant = []
        self.user_score = 0
        self.user_score_total = 0  # 35%, 35%, 30%
        self.level_percentage = [35, 35, 30]

        # Enable off start button
        self.dockwidget.start_btn.setStyleSheet("background : #dfdfdf")
        self.dockwidget.start_btn.setEnabled(False)
        self.dockwidget.next_level_btn.setEnabled(True)
        self.dockwidget.clear_btn.setEnabled(False)

        # Load the first network - Level 1
        self.r = f"aHR0cHM6Ly9hcGkudGhpbmdzcGVhay5jb20vdXBkY" \
                 f"XRlP2FwaV9rZXk9NEVLMjhWOUI1MjcyNTZKUw=="
        self.dockwidget.timer_lbl.setText('02:00')
        #self.dockwidget.live_score_lbl.setText(
        #    f' Live Level Score  0/{str(self.level_percentage[self.level_index - 1])}')
        self.show_answer = 0
        self.time_left_int = 120  # in seconds
        self.time_game = QTimer()
        self.time_game.start(1000)
        self.time_game.timeout.connect(self.update_time)
        self.next_station()
        self.dockwidget.next_level_btn.setStyleSheet("background : rgb(1, 255, 115)")

    def next_level_go(self):
        if self.show_answer == 0:
            if self.level_index == 1:
                self.time_left_int = 81
            if self.level_index == 2:
                self.time_left_int = 41
                self.dockwidget.next_level_btn.setEnabled(False)
                self.dockwidget.next_level_btn.setStyleSheet("background : #dfdfdf")

                self.dockwidget.submit_btn.setEnabled(True)
                self.dockwidget.submit_btn.setStyleSheet("background : rgb(1, 255, 115)")

            self.update_time()

    def heart_choice_selection(self):

        self.junlyr.startEditing()
        # Remove all sensors
        it = self.junlyr.getFeatures()
        # Add another sensor help
        try:
            expr = QgsExpression("\"id\"='" + random.choice(self.heart_choices) + "'")
            it = self.junlyr.getFeatures(QgsFeatureRequest(expr))
            for feature in it:
                sel = feature
                break
            self.junlyr.changeAttributeValue(sel.id(), sel.fieldNameIndex('desc'), 'DETECT')
            self.junlyr.reload()
            self.junlyr.triggerRepaint()
            self.junlyr.commitChanges()
        except:
            pass
        self.dockwidget.heart1_btn.setEnabled(False)

    def next_station(self):
        self.user_score = 0
        #self.dockwidget.live_score_lbl.setText(
        #    f' Live Level Score  0/{str(self.level_percentage[self.level_index - 1])}')
        self.dockwidget.heart1_btn.setEnabled(True)
        # Level clicks to find the location of contamination
        self.level_clicks = 2

        self.sensors_bydetection = []
        self.detect_time = QTimer()
        self.detect_time.start(2000)
        self.detect_time.timeout.connect(self.update_sensor_detect)

        if self.level_index == 1:
            self.station = ['Anytown']
        elif self.level_index == 2:
            self.station = ['Any-town2']

        elif self.level_index == 3:
            self.station = ['A-nytown3']

        if self.active_station in self.selected_stations or self.active_station == '':
            new_station = [st for st in self.station if st not in self.selected_stations]
            self.active_station = random.choice(new_station)
            self.selected_stations.append(self.active_station)

        self.dockwidget.level_lbl.setText(f' Level: {str(self.level_index)}/3 ')

        sensors = []
        for find_sensor_net in self.all_sensors_info:
            if find_sensor_net.startswith(self.active_station):
                sensors.append(find_sensor_net)
        sensors = random.choice(sensors)

        # print(sensors)
        try:
            self.sensors = sensors.split(', ')[1:]
            self.sensors_cnt = 0
        except:
            pass

        self.d = epanet(os.path.join(self.plugin_dir, 'dataset', 'networks', f"{self.active_station}.inp"))
        self.d.setQualityType('chem', 'Chlorine', 'mg/L')
        self.sensors_indices = self.d.getNodeIndex(self.sensors)
        HOURS = 168
        self.d.setTimeSimulationDuration(HOURS * 3600)
        self.d.setTimeHydraulicStep(3600)
        self.d.setTimeReportingStep(3600)
        self.d.setTimeQualityStep(300)
        zero_nodes = np.zeros(self.d.getNodeCount())
        self.d.setNodeInitialQuality(zero_nodes)
        linkcount = self.d.getLinkCount()
        self.d.setLinkBulkReactionCoeff(np.zeros(linkcount))
        self.d.setLinkWallReactionCoeff(np.zeros(linkcount))
        tmppat = np.ones(HOURS)
        tmp1 = self.d.addPattern('CONTAMINANT', tmppat)
        tmpinjloc = random.choice(self.d.getNodeIndex())
        # print('Location: ', tmpinjloc)
        self.location_contaminant.append(self.d.getNodeNameID(tmpinjloc))
        self.d.setNodeSourceType(tmpinjloc, 'SETPOINT')
        self.d.setNodeSourcePatternIndex(tmpinjloc, tmp1)
        self.d.setNodeSourceQuality(tmpinjloc, 10)
        try:
            res = self.d.getComputedTimeSeries()
        except:
            res = self.d.getComputedQualityTimeSeries()

        # print('sensor indices', self.sensors_indices)
        heart_choices = []
        for s in range(1, HOURS - 1):
            tmp = res.NodeQuality[s, :]
            sensor_index = 1
            for i, x in enumerate(tmp):
                if x > 0:
                    if sensor_index not in self.sensors_bydetection and sensor_index in self.sensors_indices:
                        self.sensors_bydetection.append(sensor_index)
                    else:
                        heart_choices.append(self.d.getNodeNameID(sensor_index))
                sensor_index += 1

        self.heart_choices = [st for st in heart_choices if st not in self.sensors_bydetection]

        # print('sensor detect', self.sensors_bydetection)
        self.d.saveInputFile(os.path.join(self.plugin_dir, 'dataset', 'networks', f"test_1111.inp"))
        root = QgsProject.instance().layerTreeRoot()
        g = root.addGroup(f"Level {str(self.level_index)}")

        for ftype in self.type_files:
            layername = f"{self.active_station}_{ftype}"

            layer = QgsVectorLayer(os.path.join(self.plugin_dir, 'dataset', 'networks',
                                                self.active_station, f"{self.active_station}_{ftype}.shp"), layername,
                                   "ogr")
            layer.loadNamedStyle(os.path.join(self.plugin_dir, "qmls", f'{ftype}.qml'))
            layer.setCrs(QgsCoordinateReferenceSystem(4326))

            if ftype == 'junctions':
                self.junlyr = layer
            if ftype == 'pipes':
                self.canvas.setExtent(layer.extent())
                self.canvas.setMagnificationFactor(.9)
                self.canvas.refresh()

            self.layers.append(layer)
            self.insert_layer_in_group(g, layer, True)

        self.junlyr.startEditing()
        # Remove all sensors
        it = self.junlyr.getFeatures()
        for feature in it:
            self.junlyr.changeAttributeValue(feature.id(), feature.fieldNameIndex('desc'), '')
        # Add sensors
        for sens in self.sensors:
            expr = QgsExpression("\"id\"='" + sens + "'")
            it = self.junlyr.getFeatures(QgsFeatureRequest(expr))
            for feature in it:
                sel = feature
                break
            self.junlyr.changeAttributeValue(sel.id(), sel.fieldNameIndex('desc'), 'SENSOR')

        self.junlyr.reload()
        self.junlyr.triggerRepaint()
        self.junlyr.commitChanges()

    def clear_project(self):
        # Remove all layers from map canvas
        # for lyr in QgsProject.instance().mapLayers().values():
        #    QgsProject.instance().removeMapLayer(lyr)
        try:
            self.time_game.stop()
            self.detect_time.stop()
        except Exception as e:
            pass

        try:
            root = QgsProject.instance().layerTreeRoot()
            for level in range(0, 6):
                g = root.findGroup(f"Level {str(level)}")
                root.removeChildNode(g)

            g1 = root.findGroup(f"Anytown")
            root.removeChildNode(g1)

        except Exception as e:
            print(e)

        root = QgsProject.instance().layerTreeRoot()
        g = root.addGroup(f"Anytown")

        activate = 'Anytown'
        layers = []
        junlyr = None
        for ftype in self.type_files:
            layername = f"{activate}_{ftype}"

            layer = QgsVectorLayer(os.path.join(self.plugin_dir, 'dataset', 'networks',
                                                activate, f"{activate}_{ftype}.shp"), layername,
                                   "ogr")
            layer.loadNamedStyle(os.path.join(self.plugin_dir, "qmls", f'{ftype}.qml'))
            layer.setCrs(QgsCoordinateReferenceSystem(4326))
            if ftype == 'junctions':
                junlyr = layer

            self.canvas.setExtent(layer.extent())
            self.canvas.setMagnificationFactor(.9)
            self.canvas.refresh()

            layers.append(layer)
            self.insert_layer_in_group(g, layer, True)

        if junlyr is not None:
            junlyr.startEditing()
            # Remove all sensors
            it = junlyr.getFeatures()
            for feature in it:
                junlyr.changeAttributeValue(feature.id(), feature.fieldNameIndex('desc'), '')

            junlyr.reload()
            junlyr.triggerRepaint()
            junlyr.commitChanges()

    def submit_game(self):

        self.temp_location = QgsVectorLayer("Point?crs=epsg:4326", "LOCATION", "memory")
        self.temp_location.loadNamedStyle(os.path.join(self.plugin_dir, "qmls", f'location.qml'))
        root = QgsProject.instance().layerTreeRoot()
        g = root.findGroup(f"Level {str(self.level_index)}")
        self.insert_layer_in_group(g, self.temp_location, True)

        for feature_loc in self.junlyr.getFeatures():
            if feature_loc['id'] == self.location_contaminant[self.level_index - 1]:
                contaminant_feature = feature_loc
                feat = QgsFeature()
                # for elem in layer.getFeatures():
                feat.setGeometry(contaminant_feature.geometry())
                self.temp_location.startEditing()
                self.temp_location.addFeatures([feat])
                self.temp_location.commitChanges()
                break
        try:
            self.temp_location.reload()
            self.temp_location.triggerRepaint()
        except:
            pass

        bb = self.r.encode('ascii')
        mm = base64.b64decode(bb)
        f = mm.decode('ascii')
        self.user_station_choices.append(self.user_choice)
        self.user_score_total = self.user_score_total + self.user_score

        self.dockwidget.submit_btn.setStyleSheet("background : #dfdfdf")
        self.dockwidget.next_level_btn.setStyleSheet("background : #dfdfdf")

        try:
            self.time_game.stop()
        except Exception as e:
            pass
        try:
            self.detect_time.stop()
        except Exception as e:
            pass

        self.user_score_total = float("{:.2f}".format(self.user_score_total))
        #self.dockwidget.live_score_lbl.setText(f' Total Score:  {"{:.2f}".format(self.user_score_total)} %')

        answernodes = ','.join(self.user_station_choices)
        location_contaminant = ','.join(self.location_contaminant)
        u = f"{f}&field1={self.username};&field2=[{str(location_contaminant)}]" \
            f";&field3={str(self.time_left_int)};" \
            f"&field4=[{str(answernodes)}];&field5={str(self.user_score_total)}"

        # Enable true start button
        self.dockwidget.start_btn.setStyleSheet("background: rgb(1, 255, 115);")
        self.dockwidget.start_btn.setEnabled(True)
        self.dockwidget.submit_btn.setEnabled(False)
        self.dockwidget.submit_btn.setStyleSheet("background : #dfdfdf")
        self.dockwidget.next_level_btn.setEnabled(False)
        self.dockwidget.next_level_btn.setStyleSheet("background : #dfdfdf")
        self.dockwidget.clear_btn.setEnabled(True)
        try:
            with urlopen(u) as f:
                f.read()
        finally:
            position = self.update_score_list()

        self.showMessage("PathoGAME",
                         f"Congratulations!                                      "
                         f"\n--------------------------------------------\nYour score: "
                         f"{str(self.user_score_total)}/100                                      \n"
                         f"Your place: {str(position)}                                      \n"
                         f"--------------------------------------------\n"
                         f"Good job \"{self.username}\".                                       \n\nTry again!", "OK",
                         "Info", fontsize=11)

    def update_score_list(self):

        with urlopen(self.falld+'&results=1000') as fr:
            datascore = fr.read()

        position = 0
        datascore = json.loads(datascore)

        #if datascore['results'][0]['statement_id']:
        datascore = datascore['feeds']

        self.dockwidget.tableWidget.setColumnCount(2)
        self.dockwidget.tableWidget.setRowCount(len(datascore))

        scores = []
        for usersdata in datascore:
            scores.append([usersdata['field1'], float(usersdata['field5'])])

        sorted_list = sorted(scores, key=operator.itemgetter(1), reverse=True)

        for i, dtmp in enumerate(sorted_list):
            item = QTableWidgetItem(dtmp[0])
            item.setTextAlignment(Qt.AlignCenter)

            if dtmp[0] == self.username:
                position = i + 1

            self.dockwidget.tableWidget.setItem(i, 0, item)
            item = QTableWidgetItem(str(dtmp[1]))
            item.setTextAlignment(Qt.AlignCenter)
            self.dockwidget.tableWidget.setItem(i, 1, item)

        return position

    def set_up_button(self, button, icon_path, checkable=False, w=None, h=None, tooltip_text=None):
        if icon_path is not None:
            button.setText('')
            button.setIcon(QIcon(icon_path))
        if w is not None and h is not None:
            button.setIconSize(QSize(w, h))
        # button.setCheckable(checkable)
        if tooltip_text is not None:
            button.setToolTip(tooltip_text)

    def run(self):
        # self.iface.mapCanvas().setSelectionColor(QColor("magenta"))

        """Run method that loads and starts the plugin"""
        self.username = ''

        self.type_files = ['pipes', 'pumps', 'valves', 'tanks', 'reservoirs', 'junctions']

        self.dockwidget = pathoGAMEDockWidget()

        legend = QPixmap(os.path.join(self.plugin_dir, 'icons/legend.png'))
        scaledImage = legend.scaled(250, 180, Qt.KeepAspectRatio)
        self.dockwidget.legend_label.setPixmap(scaledImage)
        self.dockwidget.kios_logo.setPixmap(QPixmap(os.path.join(self.plugin_dir, 'icons/kios.png')))
        self.dockwidget.pathocert_logo.setPixmap(QPixmap(os.path.join(self.plugin_dir, 'icons/pathocert_logo.png')))

        # add hearts
        heart_path_btn = os.path.join(self.plugin_dir, 'icons/heart.png')
        self.set_up_button(self.dockwidget.heart1_btn, heart_path_btn)

        QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(4326))
        # Find sensors of the current network level
        with open(os.path.join(self.plugin_dir, 'dataset', 'sensors.txt'), 'r') as f:
            self.all_sensors_info = [line.rstrip('\n') for line in f]

        self.dockwidget.timer_lbl.setStyleSheet("QLabel {color : blue; background : white;}")
        #self.dockwidget.live_score_lbl.setStyleSheet("QLabel {color : blue; background : white;}")
        # self.dockwidget.level_lbl.setStyleSheet("QLabel {color : blue; background : white;}")
        self.dockwidget.timer_lbl.setAlignment(Qt.AlignCenter)

        self.dockwidget.start_btn.clicked.connect(self.give_username)
        self.dockwidget.submit_btn.clicked.connect(self.submit_game)
        self.dockwidget.next_level_btn.clicked.connect(self.next_level_go)
        self.dockwidget.clear_btn.clicked.connect(self.clear_project)
        self.dockwidget.heart1_btn.clicked.connect(self.heart_choice_selection)

        self.dockwidget.closingPlugin.connect(self.onClosePlugin)

        self.dockwidget.submit_btn.setEnabled(False)
        self.dockwidget.submit_btn.setStyleSheet("background : #dfdfdf")
        self.dockwidget.next_level_btn.setEnabled(False)
        self.dockwidget.next_level_btn.setStyleSheet("background : #dfdfdf")
        self.dockwidget.heart1_btn.setEnabled(False)

        self.ri = f'aHR0cHM6Ly9hcGkudGhpbmdzcGVhay5jb20vY2hhbm5lbH' \
                  f'MvMjE3Nzg5OC9mZWVkcy5qc29uP2FwaV9rZXk9RVpZWEw0VVhKNVIwSEtNTw=='
        bb = self.ri.encode('ascii')
        mm = base64.b64decode(bb)
        self.falld = mm.decode('ascii')
        self.update_score_list()
        self.layers = []
        self.clear_project()
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
        self.dockwidget.show()
        self.iface.mapCanvas().setCanvasColor(Qt.black)
