# -*- coding: utf-8 -*-
"""
Processing provider that registers all Hotspot Analysis algorithms.
"""

import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .alg_gi_star import GetisOrdGiStar
from .alg_moran_local import MoranLocal
from .alg_moran_bv import MoranLocalBV


class HotspotProvider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm(GetisOrdGiStar())
        self.addAlgorithm(MoranLocal())
        self.addAlgorithm(MoranLocalBV())

    def id(self):
        return 'hotspotanalysis'

    def name(self):
        return 'Hotspot Analysis'

    def longName(self):
        return 'Hotspot Analysis v4'

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'hotspot.png')
        return QIcon(icon_path)
