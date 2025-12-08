# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HotspotAnalysis v3.0.1
                                 A QGIS plugin
 Geographical cluster detection using LISA statistics (Getis-Ord Gi*,
 Local Moran’s I and Bivariate Moran), modernized for QGIS 3.x with
 libpysal/esda.
                             -------------------
        begin                : 2017-02-22
        updated              : 2025-08-12
        maintainer           : Abimael Cereda Junior
        email                : ceredajunior@geografiadascoisas.com.br

        original authors     : 
            Daniele Oxoli
            Gabriele Prestifilippo
            Mayra Zurbaràn
            Stanly Shaji
            Politecnico di Milano

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
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):  # pylint: disable=invalid-name
    """Load HotspotAnalysis class from file hotspot_analysis.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .hotspot_analysis import HotspotAnalysis
    return HotspotAnalysis(iface)
