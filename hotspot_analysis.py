# -*- coding: utf-8 -*-
"""
Hotspot Analysis v4.0 — QGIS Processing Plugin

Geographical cluster detection using LISA statistics:
  - Getis-Ord Gi*  (Getis & Ord 1992; Ord & Getis 1995)
  - Local Moran's I  (Anselin 1995)
  - Bivariate Local Moran's I  (Anselin et al. 2002)

Original authors : Daniele Oxoli, Gabriele Prestifilippo,
                   Mayra Zurbaràn, Stanly Shaji
                   Politecnico di Milano
Maintainer (2025): Abimael Cereda Junior
                   ceredajunior@geografiadascoisas.com.br
"""

from qgis.core import QgsApplication
from .processing.provider import HotspotProvider


class HotspotAnalysis:

    def __init__(self, iface):
        self.iface = iface
        self.provider = HotspotProvider()

    def initGui(self):
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
