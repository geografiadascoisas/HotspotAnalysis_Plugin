# -*- coding: utf-8 -*-
"""
Getis-Ord Gi* — Local spatial statistic for hot/cold spot detection.

References
----------
Getis, A. & Ord, J.K. (1992). The Analysis of Spatial Association by Use
    of Distance Statistics. Geographical Analysis, 24(3), 189–206.
Ord, J.K. & Getis, A. (1995). Local Spatial Autocorrelation Statistics:
    Distributional Issues and an Application. Geographical Analysis, 27(4),
    286–306.
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

# esda / libpysal are imported lazily inside processAlgorithm so that any
# import error (ImportError, OSError, AttributeError, etc.) is captured and
# shown to the user with the original traceback.  See dependency_error_message()
# and the pip_dependencies key in metadata.txt for the recommended install path.


class GetisOrdGiStar(QgsProcessingAlgorithm):
    """
    Computes Getis-Ord Gi* for each feature.

    The Gi* statistic (star variant) includes the focal observation itself
    in the weighted sum, unlike the non-starred Gi. This is mandatory for
    correct implementation of the Getis-Ord method and is aligned with
    GeoDa and ArcGIS behaviour.

    p-values are one-tailed, consistent with the directional hypothesis of
    the Getis-Ord test and with GeoDa's output convention.
    """

    INPUT           = 'INPUT'
    FIELD           = 'FIELD'
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
        return 'getisordgistar'

    def displayName(self):
        return 'Getis-Ord Gi*'

    def group(self):
        return 'LISA'

    def groupId(self):
        return 'lisa'

    def shortHelpString(self):
        return (
            '<p>Computes the <b>Getis-Ord Gi*</b> local spatial statistic '
            '(Getis &amp; Ord 1992; Ord &amp; Getis 1995).</p>'
            '<p>Identifies statistically significant spatial clusters of '
            '<b>high values</b> (hot spots, Z &gt; 0) and '
            '<b>low values</b> (cold spots, Z &lt; 0).</p>'
            '<p><b>Output fields</b><br>'
            '&nbsp;&nbsp;<i>Z_score</i> — standardised Gi* value<br>'
            '&nbsp;&nbsp;<i>p_value</i> — one-tailed pseudo p-value '
            '(aligned with GeoDa)</p>'
            '<p><b>p-value convention</b><br>'
            'By default, p-values are <b>one-tailed</b> — the standard '
            'approach in the spatial statistics literature (Ord &amp; Getis '
            '1995) and in major reference implementations. One-tailed tests '
            'are appropriate here because Gi* is a directional statistic: '
            'it tests specifically for high-value clusters (hot spots, '
            'Z&nbsp;&gt;&nbsp;0) or low-value clusters (cold spots, '
            'Z&nbsp;&lt;&nbsp;0).<br>'
            'Check <i>Two-tailed p-value</i> only to reproduce v1 output '
            '(p&nbsp;=&nbsp;2&nbsp;×&nbsp;one-tailed). This is provided '
            'for backward compatibility; one-tailed is recommended.</p>'
            '<p><b>Note</b>: star=True is fixed — this is what defines '
            'the Gi* statistic. See README for the full methodological '
            'discussion.</p>'
            '<p><b>References</b><br>'
            'Getis &amp; Ord (1992) Geographical Analysis 24(3).<br>'
            'Ord &amp; Getis (1995) Geographical Analysis 27(4).</p>'
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
            self.FIELD, 'Analysis field',
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
            minValue=0, defaultValue=0,
        ))

        self.addParameter(QgsProcessingParameterBoolean(
            self.TWO_TAILED,
            'Two-tailed p-value  (v1 compatibility — see help)',
            defaultValue=False,
        ))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, 'Gi* output',
        ))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):
        try:
            from esda import G_Local, Moran
            from libpysal.weights.distance import DistanceBand
            from libpysal.weights.contiguity import Queen
            from libpysal.weights import KNN
        except Exception as e:
            raise QgsProcessingException(
                f"{dependency_error_message(str(e))}\n\nOriginal error: {e}"
            )

        source       = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        field_name   = self.parameterAsString(parameters, self.FIELD, context)
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
        field_idx = source.fields().indexFromName(field_name)
        features_data = []

        for feat in source.getFeatures():
            val = feat.attributes()[field_idx]
            y_val = float(val) if val is not None else float('nan')
            geom = feat.geometry()
            if geom_type == QgsWkbTypes.PointGeometry:
                pt = geom.asPoint()
                xy = (pt.x(), pt.y())
            else:
                c = geom.centroid().asPoint()
                xy = (c.x(), c.y())
            features_data.append((feat, y_val, xy))

        y      = np.array([d[1] for d in features_data])
        coords = [d[2] for d in features_data]

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
                    z = Moran(y, w_tmp).z_norm
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

        # --- Gi* computation (star=True is mandatory) -------------------
        np.random.seed(12345)
        statistics = G_Local(y, w, star=True, transform=type_w,
                             permutations=permutations)

        feedback.setProgress(75)

        from scipy.stats import norm as _norm
        use_perm   = permutations > 0 and hasattr(statistics, 'p_sim')
        two_tailed = self.parameterAsBoolean(parameters, self.TWO_TAILED, context)
        z_arr = statistics.Zs
        if use_perm:
            # symmetric pseudo p: min of both tails so cold spots are significant too
            p_arr = np.minimum(statistics.p_sim, 1.0 - statistics.p_sim)
        else:
            p_arr = _norm.sf(np.abs(z_arr))  # 1 - Φ(|Z|), one-tailed using |Z|
        if two_tailed:
            p_arr = np.minimum(p_arr * 2.0, 1.0)

        # --- Build output -----------------------------------------------
        out_fields = QgsFields(source.fields())
        out_fields.append(QgsField('Z_score', QVariant.Double))
        out_fields.append(QgsField('p_value', QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), source.sourceCrs(),
        )

        for i, (feat, _, _) in enumerate(features_data):
            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(feat.geometry())
            zval = float(z_arr[i]) if i < len(z_arr) else float('nan')
            pval = float(p_arr[i]) if i < len(p_arr) else float('nan')
            out_feat.setAttributes(feat.attributes() + [zval, pval])
            sink.addFeature(out_feat, QgsFeatureSink.FastInsert)

        feedback.setProgress(100)
        feedback.pushInfo(
            f'Gi* complete — {len(features_data)} features  |  {threshold_used}'
        )

        style_dir = os.path.join(os.path.dirname(__file__), '..', 'layer_style')
        if source.geometryType() == QgsWkbTypes.PointGeometry:
            qml = os.path.join(style_dir, 'hotspots_class.qml')
        else:
            qml = os.path.join(style_dir, 'hotspots_class_poly.qml')
        if os.path.exists(qml):
            context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(
                StylePostProcessor.create(qml)
            )

        return {self.OUTPUT: dest_id}

    # ------------------------------------------------------------------

    def createInstance(self):
        return GetisOrdGiStar()

    def tr(self, string):
        return string
