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

from qgis.PyQt.QtGui import (QPixmap, QImage)
from qgis.PyQt.QtCore import (Qt, pyqtSignal, QCoreApplication, QFileInfo, QRectF)
from qgis.core import (QgsRectangle, QgsProject, QgsVectorLayer, QgsFeature)
from qgis.gui import (QgsMapTool, QgsRubberBand)
import os.path


class MouseClick(QgsMapTool):
    afterLeftClick = pyqtSignal()
    afterRightClick = pyqtSignal()
    afterDoubleClick = pyqtSignal()

    def __init__(self, canvas, drawSelf):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.drawSelf = drawSelf
        self.drawSelf.rb = None

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent(self, event):
        pass

    def canvasDoubleClickEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):
        if self.drawSelf.show_answer > 0:
            return
        if not self.drawSelf.dockwidget.start_btn.isEnabled():
            layers = self.canvas.layers()

            self.drawSelf.user_choice = ''
            self.drawSelf.user_score = 0

            for layer in layers:
                if layer.type():
                    continue
                if layer.name() == self.drawSelf.junlyr.name():

                    try:
                        QgsProject.instance().removeMapLayer(self.temp)
                    except:
                        pass

                    p = self.toMapCoordinates(event.pos())
                    w = self.canvas.mapUnitsPerPixel() * 10
                    try:
                        rect = QgsRectangle(p.x() - w, p.y() - w, p.x() + w, p.y() + w)
                    except:
                        return

                    lRect = self.canvas.mapSettings().mapToLayerCoordinates(layer, rect)
                    layer.selectByRect(lRect)
                    selected_features = layer.selectedFeatures()

                    if selected_features:
                        feature = selected_features[0]
                        if len(QgsProject.instance().mapLayersByName("SENSORS")) == 0:
                            self.temp = QgsVectorLayer("Point?crs=epsg:4326", "SENSORS", "memory")
                            self.temp.loadNamedStyle(os.path.join(self.drawSelf.plugin_dir, "qmls", f'sensors.qml'))
                            root = QgsProject.instance().layerTreeRoot()
                            g = root.findGroup(f"Level {str(self.drawSelf.level_index)}")
                            self.drawSelf.insert_layer_in_group(g, self.temp, True)
                        else:
                            for x in self.canvas.layers():
                                if x.name() == "SENSORS":
                                    self.temp = x

                        self.drawSelf.user_choice = feature.attributes()[feature.fieldNameIndex('id')]

                        self.temp.startEditing()
                        # add a feature
                        feat = QgsFeature()
                        # for elem in layer.getFeatures():
                        feat.setGeometry(feature.geometry())

                        self.temp.addFeatures([feat])
                        self.temp.commitChanges()

                        index_selected = self.drawSelf.d.getNodeIndex(self.drawSelf.user_choice)
                        tmp = self.drawSelf.d.getConnectivityMatrix()[:, index_selected]
                        find_indices = []
                        for i, ftmp in enumerate(tmp):
                            if ftmp == 1:
                                find_indices.append(i+1)
                        # print(index_selected)
                        # print(find_indices)
                        location_index = self.drawSelf.d.getNodeIndex(self.drawSelf.location_contaminant)
                        # print(location_index)

                        time_remaining = 40
                        level_points = 35
                        if location_index[self.drawSelf.level_index-1] == index_selected:
                            proximity_factor = 1
                            time_remaining = 40
                            if self.drawSelf.level_index == 1:
                                time_remaining = 40-self.drawSelf.time_left_int
                                level_points = 35
                            if self.drawSelf.level_index == 2:
                                time_remaining = 120-40-self.drawSelf.time_left_int
                                level_points = 35
                            if self.drawSelf.level_index == 3:
                                time_remaining = 120-80-self.drawSelf.time_left_int
                                level_points = 30
                        else:
                            if index_selected in find_indices:
                                proximity_factor = 0.5
                            else:
                                proximity_factor = 0

                            if self.drawSelf.level_index == 1:
                                level_points = 35
                                time_remaining = 120 - self.drawSelf.time_left_int
                            if self.drawSelf.level_index == 2:
                                level_points = 35
                                time_remaining = 120 - 40 - self.drawSelf.time_left_int
                            if self.drawSelf.level_index == 3:
                                level_points = 30
                                time_remaining = 120 - 80 - self.drawSelf.time_left_int

                        self.drawSelf.user_score = self.score_function(level_points=level_points,
                                                                       time_remaining=time_remaining,
                                                                       proximity_factor=proximity_factor)
                        # score = "{:.2f}".format(self.drawSelf.user_score)

                        # self.drawSelf.dockwidget.live_score_lbl.setText(f" Live Level Score: "
                        #                                                f"{score}"
                        #                                                f"/{str(self.drawSelf.level_percentage[self.drawSelf.level_index-1])}")

                        try:
                            self.temp.reload()
                            self.temp.triggerRepaint()
                        except:
                            pass
                        return

    def score_function(self, level_weight=2, level_points=0, time_weight=0.25, time_remaining=0,
                       proximity_weight=10, proximity_factor=0):
        # score_function(level_weight=2, level_points=35, time_weight=0.25, time_remaining=40,
        # proximity_weight=10, proximity_factor=1)
        #
        # Level weight(level_weight) = 1 Time weight(time_weight) = 0.5
        # Proximity weight(proximity_weight) = 0.75 score_percentage represents the score as a percentage.
        # level_weight, time_weight, and proximity_weight are the weights assigned to the level points,
        # time remaining, and proximity factor, respectively. level_points represents the points earned for
        # completing a specific level. time_remaining is the time remaining for completing the level.
        # proximity_factor represents a value indicating the user's proximity to the exact contaminant location (
        # e.g., 1 for finding the exact position, 0.5 for being near, 0 for being far). total_weight is the sum of
        # the level weight, time weight, and proximity weight.
        score_percentage = ((level_weight * level_points) + (time_weight * (time_remaining - 40)) + (
                    proximity_weight * proximity_factor)) / (
                                       (level_weight * level_points) + (time_weight * (40 - 0)) + (
                                           proximity_weight * 0)) * 100
        score_percentage = (score_percentage/100)*level_points
        return score_percentage

    def deactivate(self):
        pass

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True
