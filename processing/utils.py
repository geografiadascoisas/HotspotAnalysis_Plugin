# -*- coding: utf-8 -*-
"""
Shared utilities for Hotspot Analysis processing algorithms.
"""

import os
import numpy as np

from qgis.core import QgsProcessingLayerPostProcessorInterface


class StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    """
    Applies a QML style to an output layer after it has been loaded into
    the project.  Must be registered via
    context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(...)
    because context.getMapLayer() returns None during processAlgorithm.

    The _instance class variable keeps the object alive until QGIS calls
    postProcessLayer — without it Python may garbage-collect it first.
    """
    _instance = None

    def __init__(self, qml_path):
        super().__init__()
        self._qml_path = qml_path

    def postProcessLayer(self, layer, context, feedback):
        if layer and os.path.exists(self._qml_path):
            layer.loadNamedStyle(self._qml_path)
            layer.triggerRepaint()

    @staticmethod
    def create(qml_path):
        StylePostProcessor._instance = StylePostProcessor(qml_path)
        return StylePostProcessor._instance


def min_threshold_from_coords(coords):
    """
    Compute the minimum distance threshold: the maximum nearest-neighbour
    distance across all points, ensuring every point has at least one
    neighbour within the returned distance (Ord & Getis 1995).

    Uses scipy KDTree when available; falls back to O(n²) otherwise.

    Parameters
    ----------
    coords : list of (x, y) tuples

    Returns
    -------
    float
    """
    arr = np.asarray(coords, dtype=float)
    n = len(arr)
    if n < 2:
        return 0.0

    try:
        from scipy.spatial import cKDTree
        tree = cKDTree(arr)
        dists, _ = tree.query(arr, k=2)
        return float(np.nanmax(dists[:, 1]))
    except ImportError:
        mx = 0.0
        for i in range(n):
            mind = None
            for j in range(n):
                if i == j:
                    continue
                d = float(np.sqrt(np.sum((arr[i] - arr[j]) ** 2)))
                if mind is None or d < mind:
                    mind = d
            if mind is not None and mind > mx:
                mx = mind
        return mx


def dependency_error_message(original_error: str = "") -> str:
    """
    Return a clear installation/troubleshooting message when libpysal/esda
    fail to import.  If original_error mentions 'numba' or 'NumPy', a
    targeted fix is appended.
    """
    import sys

    base = (
        "Hotspot Analysis could not load 'libpysal' / 'esda'.\n\n"
    )

    # Targeted hint for the numba/NumPy version conflict (QGIS 4.x ships
    # NumPy 2.4+; older numba builds only support ≤ 2.3).
    numba_hint = ""
    if "numba" in original_error.lower() or "numpy" in original_error.lower():
        numba_hint = (
            "Detected cause: numba version conflict with NumPy 2.4.\n"
            "Fix — open the OSGeo4W Shell and run:\n"
            "  python -m pip install --upgrade numba\n\n"
            "Alternative (avoids the numba dependency entirely):\n"
            "  python -m pip install \"libpysal<4.10\" esda\n\n"
        )

    if sys.platform.startswith("win"):
        install = (
            "General install — open the OSGeo4W Shell and run:\n"
            "  python -m pip install libpysal esda\n"
        )
    elif sys.platform == "darwin":
        install = (
            "macOS — open Terminal and run:\n"
            "  /Applications/QGIS.app/Contents/MacOS/bin/python3 "
            "-m pip install libpysal esda\n"
        )
    else:
        install = (
            "Linux — use the same Python interpreter as QGIS:\n"
            "  python3 -m pip install libpysal esda\n"
        )

    return base + numba_hint + install
