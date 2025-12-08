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
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 ***************************************************************************/
"""

import os
from PyQt5 import QtWidgets, uic

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'hotspot_analysis_dialog_base.ui')
)

class HotspotAnalysisDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)
