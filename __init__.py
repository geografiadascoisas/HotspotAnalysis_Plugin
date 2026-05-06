# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Hotspot Analysis v4.0.0
                                 A QGIS plugin
 LISA statistics for geographical cluster detection (Getis-Ord Gi*,
 Local Moran’s I, Bivariate Local Moran’s I) — Processing framework,
 QGIS 3.22+ and 4.x.
                             -------------------
        begin                : 2017-02-22
        updated              : 2026-05-06
        maintainer           : Abimael Cereda Junior
        email                : ceredajunior@geografiadascoisas.com.br

        original authors     :
            Daniele Oxoli, Gabriele Prestifilippo,
            Mayra Zurbaràn, Stanly Shaji
            (Politecnico di Milano)

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
