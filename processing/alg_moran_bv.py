# -*- coding: utf-8 -*-
"""
Bivariate Local Moran's I — LISA statistic for cross-variable spatial association.

References
----------
Anselin, L., Syabri, I. & Smirnov, O. (2002). Visualizing Multivariate
    Spatial Correlation with Dynamically Linked Windows. In Anselin &
    Rey (Eds.), New Tools for Spatial Data Analysis. CSISS.
Anselin, L. (1995). Local Indicators of Spatial Association — LISA.
    Geographical Analysis, 27(2), 93–115.

Methodological note
-------------------
The Bivariate Local Moran measures the spatial association between the
value of variable X at location i and the spatial lag of variable Y
at neighbouring locations j.  It does NOT measure the co-location
relationship between X_i and Y_i at the same site.  Interpret results
in conjunction with a univariate analysis of each variable separately.
See README for a full discussion.
"""

import os
import numpy as np

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsProcessing,
    QgsFeatureSink,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from .utils import min_threshold_from_coords, dependency_error_message, StylePostProcessor

# esda / libpysal are imported lazily inside processAlgorithm — see alg_gi_star.py.


class MoranLocalBV(QgsProcessingAlgorithm):
    """
    Bivariate Local Moran's I (Anselin et al. 2002).

    Measures the linear association between X at location i and the
    spatial lag of Y across its neighbours.

    Quadrant interpretation (same coding as univariate Moran):
      1 = HH — high X_i, high spatial lag of Y
      2 = LH — low X_i, high spatial lag of Y
      3 = LL — low X_i, low spatial lag of Y
      4 = HL — high X_i, low spatial lag of Y
    """

    INPUT           = 'INPUT'
    FIELD_X         = 'FIELD_X'
    FIELD_Y         = 'FIELD_Y'
    WEIGHTS_TYPE    = 'WEIGHTS_TYPE'
    THRESHOLD       = 'THRESHOLD'
    OPTIMIZE        = 'OPTIMIZE'
    MIN_T           = 'MIN_T'
    MAX_T           = 'MAX_T'
    STEP_T          = 'STEP_T'
    KNN_K           = 'KNN_K'
    BINARY_WEIGHTS  = 'BINARY_WEIGHTS'
    DISTANCE_METRIC = 'DISTANCE_METRIC'
    ROW_STANDARDIZE = 'ROW_STANDARDIZE'
    PERMUTATIONS    = 'PERMUTATIONS'
    TWO_TAILED      = 'TWO_TAILED'
    OUTPUT          = 'OUTPUT'

    WEIGHTS_OPTIONS  = [
        'Distance Band',
        'K-Nearest Neighbors (KNN)',
        "Queen's Contiguity (polygons only)",
    ]
    DISTANCE_OPTIONS = [
        'Euclidean — p=2 (standard for geographic data)',
        'Manhattan — p=1',
    ]

    # ------------------------------------------------------------------
    # Algorithm identity
    # ------------------------------------------------------------------

    def name(self):
        return 'moranlocalbv'

    def displayName(self):
        return "Bivariate Local Moran's I"

    def group(self):
        return 'LISA'

    def groupId(self):
        return 'lisa'

    def shortHelpString(self):
        return (
            "<p>Computes <b>Bivariate Local Moran's I</b> "
            "(Anselin et al. 2002).</p>"
            '<p>Measures the association between <b>Field X at location i</b> '
            'and the <b>spatial lag of Field Y</b> across neighbouring '
            'locations.</p>'
            '<p><b>Important</b>: this statistic does <i>not</i> measure '
            'co-location of X and Y at the same site. See README for the '
            'full methodological discussion.</p>'
            '<p><b>Output fields</b><br>'
            '&nbsp;&nbsp;<i>Z_score</i> — standardised bivariate Moran value<br>'
            '&nbsp;&nbsp;<i>p_value</i> — one-tailed pseudo p-value (aligned with GeoDa)<br>'
            '&nbsp;&nbsp;<i>q_value</i> — quadrant (1=HH, 2=LH, 3=LL, 4=HL)</p>'
            '<p><b>p-value convention</b><br>'
            'By default, p-values are <b>one-tailed</b> — the standard '
            'approach in the spatial statistics literature (Anselin et al. '
            '2002) and in major reference implementations.<br>'
            'Check <i>Two-tailed p-value</i> only to reproduce v1 output '
            '(p&nbsp;=&nbsp;2&nbsp;×&nbsp;one-tailed). This is provided '
            'for backward compatibility; one-tailed is recommended.</p>'
            '<p><b>References</b><br>'
            'Anselin et al. (2002) New Tools for Spatial Data Analysis.<br>'
            'Anselin (1995) Geographical Analysis 27(2), 93–115.</p>'
            '<p><b>Source &amp; support</b><br>'
            'Maintained by Abimael Cereda Junior. Based on original work by '
            'Daniele Oxoli et al. (Politecnico di Milano, 2017).<br>'
            '<a href="https://github.com/geografiadascoisas/HotSpotAnalysis_Plugin">'
            'github.com/geografiadascoisas/HotSpotAnalysis_Plugin</a></p>'
        )

    # ------------------------------------------------------------------
    # Parameter declaration
    # ------------------------------------------------------------------

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT, 'Input layer',
            types=[QgsProcessing.TypeVectorPoint,
                   QgsProcessing.TypeVectorPolygon],
        ))

        self.addParameter(QgsProcessingParameterField(
            self.FIELD_X, 'Field X (focal variable)',
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
        ))

        self.addParameter(QgsProcessingParameterField(
            self.FIELD_Y, 'Field Y (spatially lagged variable)',
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
        ))

        self.addParameter(QgsProcessingParameterEnum(
            self.WEIGHTS_TYPE, 'Spatial weights type',
            options=self.WEIGHTS_OPTIONS,
            defaultValue=0,
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.THRESHOLD, 'Distance threshold (Distance Band)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=0.0,
        ))

        self.addParameter(QgsProcessingParameterBoolean(
            self.OPTIMIZE, 'Optimize threshold automatically',
            defaultValue=False,
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_T, 'Minimum distance (optimization)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=0.0,
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_T, 'Maximum distance (optimization)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=0.0,
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.STEP_T, 'Step (optimization)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=1.0,
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.KNN_K, 'K neighbors (KNN)',
            type=QgsProcessingParameterNumber.Integer,
            optional=True, minValue=1, defaultValue=5,
        ))

        self.addParameter(QgsProcessingParameterBoolean(
            self.BINARY_WEIGHTS,
            'Binary weights (0/1) — unchecked = continuous (distance-decay)',
            defaultValue=True,
        ))

        self.addParameter(QgsProcessingParameterEnum(
            self.DISTANCE_METRIC, 'Distance metric',
            options=self.DISTANCE_OPTIONS,
            defaultValue=0,
        ))

        self.addParameter(QgsProcessingParameterBoolean(
            self.ROW_STANDARDIZE, 'Row standardization',
            defaultValue=False,
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.PERMUTATIONS,
            'Random permutations (0 = normal approximation)',
            type=QgsProcessingParameterNumber.Integer,
            minValue=0, defaultValue=999,
        ))

        self.addParameter(QgsProcessingParameterBoolean(
            self.TWO_TAILED,
            'Two-tailed p-value  (v1 compatibility — see help)',
            defaultValue=False,
        ))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Bivariate Local Moran's I output",
        ))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):
        try:
            from esda import Moran_Local_BV, Moran
            from libpysal.weights.distance import DistanceBand
            from libpysal.weights.contiguity import Queen
            from libpysal.weights import KNN
        except Exception as e:
            raise QgsProcessingException(
                f"{dependency_error_message(str(e))}\n\nOriginal error: {e}"
            )

        source       = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        field_x      = self.parameterAsString(parameters, self.FIELD_X, context)
        field_y      = self.parameterAsString(parameters, self.FIELD_Y, context)
        weights_type = self.parameterAsEnum(parameters, self.WEIGHTS_TYPE, context)
        binary       = self.parameterAsBoolean(parameters, self.BINARY_WEIGHTS, context)
        dist_metric  = self.parameterAsEnum(parameters, self.DISTANCE_METRIC, context)
        p_metric     = 1 if dist_metric == 1 else 2
        row_std      = self.parameterAsBoolean(parameters, self.ROW_STANDARDIZE, context)
        permutations = self.parameterAsInt(parameters, self.PERMUTATIONS, context)
        type_w       = 'R' if row_std else 'B'

        geom_type = source.geometryType()

        if geom_type == QgsWkbTypes.PolygonGeometry and weights_type != 2:
            feedback.pushWarning(
                "Polygon layer detected — switching to Queen's Contiguity automatically."
            )
            weights_type = 2

        if geom_type == QgsWkbTypes.PointGeometry and weights_type == 2:
            raise QgsProcessingException(
                "Queen's Contiguity requires a polygon layer."
            )

        # --- Collect field values and coordinates in one pass -----------
        idx_x = source.fields().indexFromName(field_x)
        idx_y = source.fields().indexFromName(field_y)
        features_data = []

        for feat in source.getFeatures():
            attrs = feat.attributes()
            x_val = float(attrs[idx_x]) if attrs[idx_x] is not None else float('nan')
            y_val = float(attrs[idx_y]) if attrs[idx_y] is not None else float('nan')
            geom = feat.geometry()
            if geom_type == QgsWkbTypes.PointGeometry:
                pt = geom.asPoint()
                xy = (pt.x(), pt.y())
            else:
                c = geom.centroid().asPoint()
                xy = (c.x(), c.y())
            features_data.append((feat, x_val, y_val, xy))

        x_arr  = np.array([d[1] for d in features_data])
        y_arr  = np.array([d[2] for d in features_data])
        coords = [d[3] for d in features_data]

        feedback.setProgress(10)

        # --- Spatial weights --------------------------------------------
        if weights_type == 2:
            path = source.dataProvider().dataSourceUri().split('|')[0]
            w = Queen.from_shapefile(path)
            threshold_used = "Queen's Contiguity"

        elif weights_type == 1:
            knn_k = self.parameterAsInt(parameters, self.KNN_K, context)
            w = KNN(coords, k=knn_k, p=p_metric)
            threshold_used = f'KNN  k={knn_k}  p={p_metric}'

        else:
            optimize = self.parameterAsBoolean(parameters, self.OPTIMIZE, context)

            if optimize:
                min_t  = self.parameterAsDouble(parameters, self.MIN_T, context)
                max_t  = self.parameterAsDouble(parameters, self.MAX_T, context)
                step_t = self.parameterAsDouble(parameters, self.STEP_T, context)
                if step_t <= 0 and max_t <= 0:
                    d_min = min_threshold_from_coords(coords)
                    if d_min == 0:
                        raise QgsProcessingException(
                            "Cannot auto-derive distance range: all points appear "
                            "to share the same location."
                        )
                    min_t  = d_min
                    max_t  = d_min * 5.0
                    step_t = d_min * 0.5
                    feedback.pushInfo(
                        f'No range provided — auto-derived from data: '
                        f'min={min_t:.4f}  max={max_t:.4f}  step={step_t:.4f}'
                    )
                elif step_t <= 0 or max_t <= min_t:
                    raise QgsProcessingException(
                        "Threshold optimization requires Step > 0 and "
                        "Maximum distance > Minimum distance."
                    )
                feedback.pushInfo('Optimizing distance threshold (Moran z_norm criterion)…')
                best_t, best_z = min_t, -1e9
                for t in np.arange(min_t, max_t + step_t, step_t):
                    w_tmp = DistanceBand(coords, threshold=t, p=p_metric, binary=binary)
                    z = Moran(x_arr, w_tmp).z_norm
                    if z > best_z:
                        best_t, best_z = t, z
                threshold1 = best_t
                feedback.pushInfo(f'Optimal threshold: {threshold1:.4f}')
            else:
                threshold1 = self.parameterAsDouble(parameters, self.THRESHOLD, context)
                if not threshold1:
                    threshold1 = min_threshold_from_coords(coords)
                    feedback.pushInfo(
                        f'No threshold provided — using minimum spanning distance: '
                        f'{threshold1:.4f}'
                    )

            w = DistanceBand(coords, threshold=threshold1, p=p_metric, binary=binary)
            threshold_used = (
                f'Distance Band  threshold={threshold1:.4f}  '
                f'binary={binary}  p={p_metric}'
            )

        feedback.setProgress(40)
        feedback.pushInfo(f'Weights: {threshold_used}')

        # --- Bivariate Local Moran's I computation ----------------------
        np.random.seed(12345)
        # x_arr = focal variable (X at location i)
        # y_arr = spatially lagged variable (Y at neighbours j)
        statistics = Moran_Local_BV(x_arr, y_arr, w,
                                    transformation=type_w,
                                    permutations=permutations)

        feedback.setProgress(75)

        from scipy.stats import norm as _norm
        use_perm   = permutations > 0 and hasattr(statistics, 'p_sim')
        two_tailed = self.parameterAsBoolean(parameters, self.TWO_TAILED, context)
        if use_perm:
            z_arr_out = statistics.z_sim
            p_arr_out = np.minimum(statistics.p_sim, 1.0 - statistics.p_sim)
        else:
            z_arr_out = statistics.z_norm
            p_arr_out = _norm.sf(np.abs(z_arr_out))
        if two_tailed:
            p_arr_out = np.minimum(p_arr_out * 2.0, 1.0)

        q_arr = getattr(statistics, 'q', None)

        # --- Build output -----------------------------------------------
        out_fields = QgsFields(source.fields())
        out_fields.append(QgsField('Z_score', QVariant.Double))
        out_fields.append(QgsField('p_value', QVariant.Double))
        out_fields.append(QgsField('q_value', QVariant.Int))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), source.sourceCrs(),
        )

        for i, (feat, _, _, _) in enumerate(features_data):
            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(feat.geometry())
            zval = float(z_arr_out[i]) if i < len(z_arr_out) else float('nan')
            pval = float(p_arr_out[i]) if i < len(p_arr_out) else float('nan')
            qval = int(q_arr[i]) if q_arr is not None and i < len(q_arr) else None
            out_feat.setAttributes(feat.attributes() + [zval, pval, qval])
            sink.addFeature(out_feat, QgsFeatureSink.FastInsert)

        feedback.setProgress(100)
        feedback.pushInfo(
            f"Bivariate Local Moran's I complete — {len(features_data)} features  |  "
            f'{threshold_used}'
        )

        style_dir = os.path.join(os.path.dirname(__file__), '..', 'layer_style')
        if source.geometryType() == QgsWkbTypes.PointGeometry:
            qml = os.path.join(style_dir, 'moran_class.qml')
        else:
            qml = os.path.join(style_dir, 'moran_class_poly.qml')
        if os.path.exists(qml):
            context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(
                StylePostProcessor.create(qml)
            )

        return {self.OUTPUT: dest_id}

    # ------------------------------------------------------------------

    def createInstance(self):
        return MoranLocalBV()

    def tr(self, string):
        return string
