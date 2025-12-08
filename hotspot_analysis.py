# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Hotspot Analysis v3.0.1 (enhanced 2025)
                                 A QGIS Plugin

 This plugin implements Local Indicators of Spatial Association (LISA),
 including Getis-Ord Gi* and Moran-based cluster analysis.

 Enhanced version maintained for compatibility with modern QGIS and
 libpysal/esda libraries, with corrections to statistical output fields
 and improved robustness for educational and analytical workflows.

 -------------------
        begin                : 2017-02-22
        original authors     : Daniele Oxoli, Gabriele Prestifilippo,
                               Mayra Zurbaràn, Stanly Shaji
        email (original)     : daniele.oxoli@polimi.it
        maintenance (2025)   : Abimael Cereda Junior
        email (2025)         : ceredajunior@geografiadascoisas.com.br
        version              : 3.0.1
        date                 : 2025-12-07
        git sha              : $Format:%H$
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

from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QComboBox, QFrame, QLineEdit, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import *
from PyQt5.QtCore import QVariant

# Initialize Qt resources from file resources.py
from . import resources
# Import the code for the dialog
from .hotspot_analysis_dialog import HotspotAnalysisDialog

import os.path
import sys
import io as _io
import numpy

from esda import G_Local, Moran_Local, Moran_Local_BV, Moran
from libpysal.weights.distance import DistanceBand
from libpysal.weights.contiguity import Queen
from libpysal.weights import KNN

from osgeo import ogr, gdal

# >>> QGIS stderr/stdout guard (somente se estiverem None, sem suprimir globalmente)
if getattr(sys, 'stderr', None) is None:
    try:
        sys.stderr = sys.__stderr__
    except Exception:
        sys.stderr = _io.StringIO()

if getattr(sys, 'stdout', None) is None:
    try:
        sys.stdout = sys.__stdout__
    except Exception:
        sys.stdout = _io.StringIO()
# <<< QGIS stderr/stdout guard

# geometry type: 1 point, 3 polygon
type = 0


def pr(self, msg):
    QMessageBox.information(self.iface.mainWindow(), self.tr("Debug"), msg)


class HotspotAnalysis(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'HotspotAnalysis_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = HotspotAnalysisDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Hotspot Analysis')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'HotspotAnalysis')
        self.toolbar.setObjectName(u'HotspotAnalysis')
        # Load output directory path
        self.dlg.lineEdit.clear()
        self.dlg.pushButton.clicked.connect(self.select_output_file)
        self.clear_ui()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('HotspotAnalysis', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar."""

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
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = self.plugin_dir + '/hotspot.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Hotspot Analysis'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Hotspot Analysis'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def select_output_file(self):
        """Selects the output file directory"""
        filename, _ = QFileDialog.getSaveFileName(self.dlg, self.tr("Select output directory"))
        self.dlg.lineEdit.setText(filename)

    def optimizedThreshold(self, checked):
        """Settings for Optimized threshold"""
        if checked:
            self.dlg.lineEdit_minT.setEnabled(True)
            self.dlg.lineEdit_maxT.setEnabled(True)
            self.dlg.lineEdit_dist.setEnabled(True)
            self.dlg.lineEditThreshold.setEnabled(False)
            self.dlg.lineEditThreshold.clear()
            self.dlg.label_threshold.setEnabled(False)
            self.dlg.label_7.setEnabled(True)
            self.dlg.label_8.setEnabled(True)
            self.dlg.label_9.setEnabled(True)

        else:
            self.dlg.lineEdit_minT.setEnabled(False)
            self.dlg.lineEdit_minT.clear()
            self.dlg.lineEdit_maxT.clear()
            self.dlg.lineEdit_dist.clear()
            self.dlg.lineEdit_maxT.setEnabled(False)
            self.dlg.lineEdit_dist.setEnabled(False)
            self.dlg.lineEditThreshold.setEnabled(True)
            self.dlg.label_threshold.setEnabled(True)
            self.dlg.label_7.setEnabled(False)
            self.dlg.label_8.setEnabled(False)
            self.dlg.label_9.setEnabled(False)

    def randomPermChecked(self, checked):
        """Settings for Random permutations"""
        if checked:
            self.dlg.lineEdit_random.setEnabled(True)
        else:
            self.dlg.lineEdit_random.setEnabled(False)

    def moranBiChecked(self, checked):
        if checked:
            self.dlg.comboBox_C_2.setEnabled(True)
        else:
            self.dlg.comboBox_C_2.setEnabled(False)

    def knnChecked(self, checked):
        if checked:
            self.dlg.lineEditThreshold.clear()
            self.dlg.lineEditThreshold.setEnabled(False)
            self.dlg.knn_number.setEnabled(True)
        else:
            self.dlg.lineEditThreshold.setEnabled(True)

    def clear_ui(self):
        """Clearing the UI for new operations"""
        self.dlg.comboBox.clear()
        self.dlg.lineEdit.clear()
        self.dlg.lineEditThreshold.clear()
        self.dlg.comboBox_C.clear()
        self.dlg.comboBox_C_2.clear()
        self.dlg.comboBox_C_2.setEnabled(False)
        self.dlg.lineEditThreshold.setEnabled(True)
        self.dlg.checkBox_optimizeDistance.setChecked(False)
        self.dlg.checkBox_rowStandard.setChecked(False)
        self.dlg.checkBox_randomPerm.setChecked(False)
        self.dlg.checkBox_queen.setChecked(False)
        self.dlg.checkBox_queen.setEnabled(False)
        self.dlg.lineEdit_minT.setEnabled(False)
        self.dlg.lineEdit_maxT.setEnabled(False)
        self.dlg.lineEdit_dist.setEnabled(False)
        self.dlg.lineEdit_minT.clear()
        self.dlg.lineEdit_maxT.clear()
        self.dlg.lineEdit_dist.clear()
        self.dlg.lineEditThreshold.clear()
        self.dlg.label_7.setEnabled(False)
        self.dlg.label_8.setEnabled(False)
        self.dlg.label_9.setEnabled(False)
        self.dlg.knn_number.setEnabled(False)
        self.dlg.checkBox_knn.setChecked(False)
        self.dlg.checkBox_knn.setEnabled(True)
        self.load_comboBox()

    def clear_fields(self):
        """Clearing the fields when layers are changed"""
        self.dlg.comboBox_C.clear()
        self.dlg.comboBox_C_2.clear()

    def write_file(self, filename, statistics, layerName, inLayer, inDataSource, y, threshold1):
        """Escreve shapefile de saída. Fluxos distintos para Getis-Ord e Moran."""
        import os

        outDriver = ogr.GetDriverByName("ESRI Shapefile")

        # layerName é string no plugin original
        base = layerName.split('.')
        if base:
            base.pop()
        outShapefile = filename + ".shp"

        # remove saída anterior
        if os.path.exists(outShapefile):
            try:
                outDriver.DeleteDataSource(outShapefile)
            except Exception:
                pass

        outDataSource = outDriver.CreateDataSource(outShapefile)
        outLayer = outDataSource.CreateLayer(
            "output",
            inLayer.GetSpatialRef(),
            inLayer.GetLayerDefn().GetGeomType()
        )

        # copia campos originais
        inLayerDefn = inLayer.GetLayerDefn()
        for i in range(0, inLayerDefn.GetFieldCount()):
            fieldDefn = inLayerDefn.GetFieldDefn(i)
            outLayer.CreateField(fieldDefn)

        # campos de saída comuns
        Z_field = ogr.FieldDefn("Z-score", ogr.OFTReal)
        Z_field.SetWidth(15)
        Z_field.SetPrecision(10)
        outLayer.CreateField(Z_field)

        p_field = ogr.FieldDefn("p-value", ogr.OFTReal)
        p_field.SetWidth(15)
        p_field.SetPrecision(10)
        outLayer.CreateField(p_field)

        # q-value só para Moran (local univariado/bivariado), nunca para Getis-Ord
        if (self.dlg.checkBox_moran.isChecked() == 1 or self.dlg.checkBox_moranBi.isChecked() == 1):
            q_field = ogr.FieldDefn("q-value", ogr.OFTInteger)
            q_field.SetWidth(10)
            outLayer.CreateField(q_field)

        outLayerDefn = outLayer.GetLayerDefn()
        inLayerDefn = inLayer.GetLayerDefn()

        use_perm = (getattr(statistics, "permutations", 0) > 0)

        # Garantir início da leitura
        inLayer.ResetReading()

        for i, inFeature in enumerate(inLayer):
            outFeature = ogr.Feature(outLayerDefn)

            # copia atributos
            for j in range(0, inLayerDefn.GetFieldCount()):
                outFeature.SetField(
                    outLayerDefn.GetFieldDefn(j).GetNameRef(),
                    inFeature.GetField(j)
                )

            # geometria
            geom = inFeature.GetGeometryRef()
            outFeature.SetGeometry(geom.Clone() if geom is not None else None)

            if self.dlg.checkBox_gi.isChecked() == 1:
                # -------- Getis-Ord G* --------
                # atributos disponíveis em G_Local:
                #   - Zs (aprox. normal)
                #   - p_sim (se permutations>0) ou p_norm (se normal)
                #   - NÃO há 'q' em Getis-Ord
                try:
                    if use_perm and hasattr(statistics, 'p_sim'):
                        pval = statistics.p_sim
                    else:
                        pval = statistics.p_norm

                    zarr = statistics.Zs

                    if zarr is not None and i < len(zarr):
                        zval = float(zarr[i])
                    else:
                        zval = float('nan')

                    if pval is not None and i < len(pval):
                        p_raw = float(pval[i])
                        p_out = min(1.0, 2.0 * (p_raw if p_raw <= 0.5 else (1.0 - p_raw)))
                    else:
                        p_out = float('nan')

                    outFeature.SetField("Z-score", zval)
                    outFeature.SetField("p-value", p_out)
                except Exception:
                    outFeature.SetField("Z-score", float('nan'))
                    outFeature.SetField("p-value", float('nan'))

            else:  # -------- Moran Local (uni/bivariado) --------
                try:
                    from math import erfc, sqrt

                    if use_perm:
                        if hasattr(statistics, 'z_sim') and i < len(statistics.z_sim):
                            zval = float(statistics.z_sim[i])
                        else:
                            zval = float('nan')

                        if hasattr(statistics, 'p_sim') and i < len(statistics.p_sim):
                            p_raw = float(statistics.p_sim[i])
                            p_out = min(1.0, 2.0 * (p_raw if p_raw <= 0.5 else (1.0 - p_raw)))
                        else:
                            p_out = float('nan')
                    else:
                        if hasattr(statistics, 'z_norm') and i < len(statistics.z_norm):
                            zval = float(statistics.z_norm[i])
                            p_out = erfc(abs(zval) / sqrt(2.0))
                        else:
                            zval = float('nan')
                            p_out = float('nan')

                    outFeature.SetField("Z-score", zval)
                    outFeature.SetField("p-value", p_out)

                    qarr = getattr(statistics, 'q', None)
                    if qarr is not None and i < len(qarr):
                        try:
                            outFeature.SetField("q-value", int(qarr[i]))
                        except Exception:
                            outFeature.SetField("q-value", None)
                except Exception:
                    outFeature.SetField("Z-score", float('nan'))
                    outFeature.SetField("p-value", float('nan'))

            outLayer.CreateFeature(outFeature)
            outFeature = None

        # fecha e carrega
        inDataSource.Destroy()
        outDataSource.Destroy()

        if threshold1:
            self.success_msg(threshold1)

        new_layer = self.iface.addVectorLayer(
            filename + ".shp",
            str(os.path.basename(os.path.normpath(filename))),
            "ogr"
        )
        if not new_layer:
            QMessageBox.information(
                self.dlg,
                self.tr("Hotspot Analysis"),
                self.tr("The output layer could not be loaded."),
                QMessageBox.Ok)
        self.clear_ui()

    def load_comboBox(self):
        """Load the numeric fields into combobox when layers are changed."""

        layer_shp = []
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]

        # List only shapefiles in project
        if len(layers) != 0:
            for layer in layers:
                if hasattr(layer, "dataProvider"):
                    myfilepath = layer.dataProvider().dataSourceUri()
                    (_, nameFile) = os.path.split(myfilepath)
                    if nameFile.lower().endswith(".shp"):
                        layer_shp.append(layer)

        selectedLayerIndex = self.dlg.comboBox.currentIndex()

        # Avoid out-of-range errors
        if selectedLayerIndex < 0 or selectedLayerIndex >= len(layer_shp):
            return

        try:
            selectedLayer = layer_shp[selectedLayerIndex]
        except Exception:
            return

        # ---------- FILTER NUMERIC FIELDS ONLY ----------
        numeric_fields = []
        for field in selectedLayer.fields():
            if field.type() in (
                QVariant.Int,
                QVariant.Double,
                QVariant.LongLong,
                QVariant.UInt,
                QVariant.ULongLong
            ):
                numeric_fields.append(field.name())

        # Clear and update UI
        self.clear_fields()
        self.dlg.comboBox_C.addItems(numeric_fields)
        self.dlg.comboBox_C_2.addItems(numeric_fields)

        # ---------- Continue original logic ----------
        path = selectedLayer.dataProvider().dataSourceUri().split('|')[0]

        inDriver = ogr.GetDriverByName("ESRI Shapefile")
        inDataSource = inDriver.Open(path, 0)
        inLayer = inDataSource.GetLayer()

        global type
        type = inLayer.GetLayerDefn().GetGeomType()

        if type == 3:  # polygon
            self.dlg.checkBox_queen.setChecked(True)
            self.dlg.lineEditThreshold.setEnabled(False)
            self.dlg.checkBox_knn.setEnabled(False)
            self.dlg.knn_number.setEnabled(False)
            self.dlg.checkBox_optimizeDistance.setChecked(False)
            self.dlg.checkBox_optimizeDistance.setEnabled(False)
            self.dlg.lineEdit_minT.setEnabled(False)
            self.dlg.lineEdit_maxT.setEnabled(False)
            self.dlg.lineEdit_dist.setEnabled(False)

        else:  # point
            self.dlg.checkBox_queen.setChecked(False)
            self.dlg.checkBox_knn.setEnabled(True)
            self.dlg.knn_number.setEnabled(True)
            self.dlg.lineEditThreshold.setEnabled(True)
            self.dlg.checkBox_optimizeDistance.setEnabled(True)
            self.dlg.lineEdit_minT.setEnabled(True)
            self.dlg.lineEdit_dist.setEnabled(True)
            self.dlg.lineEdit_maxT.setEnabled(True)
            thresh = _hs_min_threshold_from_shapefile(path)
            self.dlg.lineEditThreshold.setText(str(int(thresh)))

        inDataSource.Destroy()

    def error_msg(self):
        """Message to report missing or invalid input fields."""
        self.clear_ui()
        self.loadLayerList()
        QMessageBox.warning(
            self.dlg,
            self.tr("Hotspot Analysis: Warning"),
            self.tr("Please provide all required input fields correctly."),
            QMessageBox.Ok)

    def success_msg(self, distance):
        """Message to report successful file creation."""
        QMessageBox.information(
            self.dlg,
            self.tr("Hotspot Analysis: Success"),
            self.tr(f"Output file generated successfully (Distance used = {distance})"),
            QMessageBox.Ok)

    def validator(self):
        """Validator to Check whether the inputs are given properly"""

        # Polygon case
        if self.dlg.checkBox_queen.isChecked() == 1:
            return 1

        if ((self.dlg.checkBox_optimizeDistance.isChecked() == 0
             and self.dlg.lineEditThreshold.text() != "")
            or (self.dlg.checkBox_optimizeDistance.isChecked() == 1
                and (self.dlg.lineEdit_dist.text() != ""
                     and self.dlg.lineEdit_maxT.text() != ""
                     and self.dlg.lineEdit_minT.text() != "")) or
                (self.dlg.checkBox_knn.isChecked() == 1)) \
                and self.dlg.lineEdit.text() != "":
            return 1
        else:
            return 0

    def loadLayerList(self):
        """Load shapefile layers and populate numeric attribute fields safely."""

        layers_list = []
        layers_shp = []

        # Show the shapefiles in the ComboBox
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]

        if len(layers) != 0:
            for layer in layers:
                if hasattr(layer, "dataProvider"):
                    myfilepath = layer.dataProvider().dataSourceUri()
                    (_, nameFile) = os.path.split(myfilepath)

                    if nameFile.lower().endswith(".shp"):
                        layers_list.append(layer.name())
                        layers_shp.append(layer)

            # Populate list of layers in the ComboBox
            self.dlg.comboBox.clear()
            self.dlg.comboBox.addItems(layers_list)

            selectedLayerIndex = self.dlg.comboBox.currentIndex()

            # Safety: avoid invalid index
            if selectedLayerIndex < 0 or selectedLayerIndex >= len(layers_shp):
                return [layers, layers_shp]

            selectedLayer = layers_shp[selectedLayerIndex]

            # ---------- FILTER NUMERIC FIELDS ONLY ----------
            numeric_fields = []
            for field in selectedLayer.fields():
                if field.type() in (
                    QVariant.Int,
                    QVariant.Double,
                    QVariant.LongLong,
                    QVariant.UInt,
                    QVariant.ULongLong
                ):
                    numeric_fields.append(field.name())

            # Populate attribute ComboBoxes
            self.clear_fields()
            self.dlg.comboBox_C.addItems(numeric_fields)
            self.dlg.comboBox_C_2.addItems(numeric_fields)

            # ---------- SIGNAL BINDINGS ----------
            try:
                self.dlg.comboBox.activated.connect(lambda: self.load_comboBox())
                self.dlg.comboBox.currentIndexChanged.connect(lambda: self.load_comboBox())
                self.dlg.checkBox_optimizeDistance.toggled.connect(self.optimizedThreshold)
                self.dlg.checkBox_randomPerm.toggled.connect(self.randomPermChecked)
                self.dlg.checkBox_moranBi.toggled.connect(self.moranBiChecked)
                self.dlg.checkBox_knn.toggled.connect(self.knnChecked)
            except Exception:
                return False

            return [layers, layers_shp]

        else:
            return [layers, False]

    def run(self):
        """Run method that performs all the real work"""

        self.clear_ui()
        layers, layers_shp = self.loadLayerList()
        if len(layers) == 0:
            return

        self.dlg.show()
        self.load_comboBox()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed and fields are not empty
        if result and (self.validator() == 1):
            selectedLayerIndex = self.dlg.comboBox.currentIndex()
            if selectedLayerIndex < 0 or selectedLayerIndex > len(layers):
                return

            selectedLayer = layers_shp[selectedLayerIndex]
            layerName = selectedLayer.dataProvider().dataSourceUri()
            C = selectedLayer.fields().indexFromName(self.dlg.comboBox_C.currentText())
            C2 = selectedLayer.fields().indexFromName(self.dlg.comboBox_C_2.currentText())
            filename = self.dlg.lineEdit.text()
            path = layerName.split('|')[0]

            inDriver = ogr.GetDriverByName("ESRI Shapefile")
            inDataSource = inDriver.Open(path, 0)
            inLayer = inDataSource.GetLayer()

            global type
            type = inLayer.GetLayerDefn().GetGeomType()

            # Vetor de atributos principal (y)
            u = []
            inLayer.ResetReading()
            for feature in inLayer:
                u.append(feature.GetField(C))
            y = numpy.array(u)

            # Vetor secundário (x) para Moran Bivariado
            if self.dlg.checkBox_moranBi.isChecked() == 1:
                v = []
                inLayer.ResetReading()
                for feature in inLayer:
                    v.append(feature.GetField(C2))
                x = numpy.array(v)

            # Construção da matriz de pesos espaciais
            if type == 1:  # point
                t = ()
                inLayer.ResetReading()
                for feature in inLayer:
                    geometry = feature.GetGeometryRef()
                    if geometry is None:
                        continue
                    xy = (geometry.GetX(), geometry.GetY())
                    t = t + (xy,)

                if self.dlg.lineEditThreshold.text() and self.dlg.lineEditThreshold.text() != "":  # threshold definido
                    threshold1 = int(self.dlg.lineEditThreshold.text())

                elif self.dlg.checkBox_knn.isChecked() == 0:  # otimizar threshold (sem KNN)
                    mx_moran = -1000.0
                    mx_i = -1000.0
                    minT = int(self.dlg.lineEdit_minT.text())
                    maxT = int(self.dlg.lineEdit_maxT.text())
                    dist = int(self.dlg.lineEdit_dist.text())
                    for i in range(minT, maxT + dist, dist):
                        w_tmp = DistanceBand(t, threshold=i, p=2, binary=True)
                        moran = Moran(y, w_tmp)
                        if moran.z_norm > mx_moran:
                            mx_i = i
                            mx_moran = moran.z_norm
                    threshold1 = int(mx_i)

                if self.dlg.checkBox_knn.isChecked() == 1:
                    weightValue = int(self.dlg.knn_number.text())
                    w = KNN.from_shapefile(layerName.split("|")[0], k=weightValue, p=2)
                    threshold1 = "None / KNN used - K = " + self.dlg.knn_number.text()
                else:
                    w = DistanceBand(t, threshold1, p=2, binary=True)
            else:  # polygon
                w = Queen.from_shapefile(layerName.split("|")[0])
                threshold1 = "None / Queen's Case used"

            if self.dlg.checkBox_rowStandard.isChecked() == 1:
                type_w = "R"
            else:
                type_w = "B"

            # Permutações
            if self.dlg.checkBox_randomPerm.isChecked() == 1:
                permutationsValue = int(self.dlg.lineEdit_random.text())
            else:
                if self.dlg.checkBox_gi.isChecked() == 1:
                    # Para Getis-Ord, sempre usar aproximação normal (p_norm)
                    permutationsValue = 0
                else:
                    # Para Moran, usar permutação (mais confiável)
                    permutationsValue = 999

            numpy.random.seed(12345)

            if self.dlg.checkBox_gi.isChecked() == 1:
                statistics = G_Local(y, w, transform=type_w, permutations=permutationsValue)
            elif self.dlg.checkBox_moran.isChecked() == 1:
                statistics = Moran_Local(y, w, transformation=type_w, permutations=permutationsValue)
            else:
                statistics = Moran_Local_BV(y, x, w, transformation=type_w, permutations=permutationsValue)

            self.write_file(
                filename,
                statistics,
                layerName,
                inLayer,
                inDataSource,
                y,
                threshold1
            )

            # assign the style to the output layer on QGIS
            if self.dlg.checkBox_gi.isChecked() == 1:
                if type == 1:  # point
                    stylePath = "/layer_style/hotspots_class.qml"
                else:
                    stylePath = "/layer_style/hotspots_class_poly.qml"
                self.iface.activeLayer().loadNamedStyle(os.path.dirname(__file__) + stylePath)
            else:
                if type == 1:  # point
                    stylePath = "/layer_style/moran_class.qml"
                else:
                    stylePath = "/layer_style/moran_class_poly.qml"
                self.iface.activeLayer().loadNamedStyle(os.path.dirname(__file__) + stylePath)

        elif result and (self.validator() == 0):
            self.error_msg()
        else:
            self.clear_ui()
        pass


# >>> HS helper min-threshold (auto-patch)
def _hs_min_threshold_from_shapefile(path):
    from osgeo import ogr
    import numpy as np
    try:
        from scipy.spatial import cKDTree as KDTree
        use_scipy = True
    except Exception:
        use_scipy = False

    ds = ogr.Open(path)
    if ds is None:
        raise RuntimeError("Cannot open shapefile: %s" % path)
    lyr = ds.GetLayer(0)
    coords = []
    for feat in lyr:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        try:
            name = geom.GetGeometryName().upper()
            if name.startswith("POINT"):
                x = geom.GetX()
                y = geom.GetY()
            else:
                c = geom.Centroid()
                x = c.GetX()
                y = c.GetY()
            coords.append((x, y))
        except Exception:
            continue
    ds.Destroy()
    n = len(coords)
    if n < 2:
        return 0.0
    arr = np.asarray(coords, dtype=float)
    if use_scipy:
        tree = KDTree(arr)
        dists, _ = tree.query(arr, k=2)
        nn = dists[:, 1]
        return float(np.nanmax(nn))
    else:
        # O(n^2) fallback
        mx = 0.0
        for i in range(n):
            mind = None
            xi = arr[i]
            for j in range(n):
                if i == j:
                    continue
                dx = xi[0] - arr[j, 0]
                dy = xi[1] - arr[j, 1]
                d = (dx * dx + dy * dy) ** 0.5
                if mind is None or d < mind:
                    mind = d
            if mind is not None and mind > mx:
                mx = mind
        return float(mx)
# <<< HS helper min-threshold (auto-patch)
