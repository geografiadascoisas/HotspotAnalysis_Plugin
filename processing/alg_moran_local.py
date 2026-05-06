# -*- coding: utf-8 -*-
"""
Local Moran's I — Univariate LISA statistic for cluster/outlier detection.

References
----------
Anselin, L. (1995). Local Indicators of Spatial Association — LISA.
    Geographical Analysis, 27(2), 93–115.
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

from .utils import min_threshold_from_coords, dependency_error_message, StylePostProcessor, fdr_bh

# esda / libpysal are imported lazily inside processAlgorithm — see alg_gi_star.py.


class MoranLocal(QgsProcessingAlgorithm):
    """
    Univariate Local Moran's I (Anselin 1995).

    Classifies each feature into one of four quadrants:
      1 = HH (High-High)  — spatial cluster of high values
      2 = LH (Low-High)   — spatial outlier: low surrounded by high
      3 = LL (Low-Low)    — spatial cluster of low values
      4 = HL (High-Low)   — spatial outlier: high surrounded by low

    p-values are one-tailed pseudo p-values from conditional randomisation,
    consistent with Anselin (1995) and GeoDa's output convention.
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
        return 'moranlocal'

    def displayName(self):
        return "Univariate Local Moran’s I"

    def group(self):
        return 'LISA'

    def groupId(self):
        return 'lisa'

    def shortHelpString(self):
        return (
            "<p>Computes <b>Local Moran's I</b> for each feature, classifying spatial "
            'association into four quadrant types:<br>'
            '&nbsp;&nbsp;· HH (1) — high value surrounded by high values<br>'
            '&nbsp;&nbsp;· LH (2) — low value surrounded by high values<br>'
            '&nbsp;&nbsp;· LL (3) — low value surrounded by low values<br>'
            '&nbsp;&nbsp;· HL (4) — high value surrounded by low values</p>'
            '<p><b>Parameters</b><br>'
            '<i>Input layer</i> — Point or polygon vector layer.<br>'
            '<i>Analysis field</i> — Numeric field containing the values to analyse.<br>'
            '<i>Spatial weights type</i> — How neighbours are defined:<br>'
            '&nbsp;&nbsp;· Distance Band — all features within a given distance<br>'
            '&nbsp;&nbsp;· KNN — a fixed number of nearest neighbours<br>'
            '&nbsp;&nbsp;· Queen Contiguity — features sharing a border or vertex (polygons only)<br>'
            '<i>Distance threshold</i> — Maximum distance to consider a feature a neighbour '
            '(Distance Band). Leave empty to use the optimised value.<br>'
            '<i>Optimize threshold automatically</i> — Finds the distance that maximises '
            'spatial autocorrelation within the Min / Max / Step range.<br>'
            '<i>Minimum / Maximum / Step</i> — Search bounds for automatic threshold optimisation.<br>'
            '<i>K neighbors</i> — Number of nearest neighbours (KNN only).<br>'
            '<i>Binary weights</i> — Checked: neighbours count equally. Unchecked: weight decreases with distance.<br>'
            '<i>Distance metric</i> — Formula used to measure distances between features.<br>'
            '<i>Row standardization</i> — Normalises each row so weights sum to 1. '
            'Useful when features have unequal numbers of neighbours.<br>'
            '<i>Random permutations</i> — Monte Carlo simulations to compute the p-value. '
            'Default 999. 0 = analytical approximation.<br>'
            '<i>Two-tailed p-value</i> — Compatibility with plugin v1 output. '
            'Not recommended; one-tailed is the standard.</p>'
            '<p><b>Output fields</b><br>'
            '<i>Z_score</i> — standardised local Moran value<br>'
            '<i>p_value</i> — one-tailed pseudo p-value<br>'
            '<i>q_value</i> — spatial quadrant: 1 = HH, 2 = LH, 3 = LL, 4 = HL<br>'
            '<i>p_fdr</i> — Benjamini-Hochberg adjusted p-value for multiple comparisons '
            '(Caldas de Castro &amp; Singer 2006)</p>'
            '<p><b>NULL / NaN values</b><br>'
            'Features with NULL or NaN in the analysis field are automatically excluded from '
            'computation (their output fields will be NaN). A warning is shown in the log. '
            'This follows the GeoDa convention (Caldas de Castro &amp; Singer 2006).</p>'
            '<p><b>References</b><br>'
            'Anselin (1995) Geographical Analysis 27(2), 93–115.<br>'
            'Caldas de Castro &amp; Singer (2006) Geographical Analysis 38(2).</p>'
            '<p><b>Documentation and Source</b><br>'
            'Maintained by Abimael Cereda Junior. Based on original work by '
            'Daniele Oxoli et al. (Politecnico di Milano, 2017).<br>'
            '<a href="https://github.com/geografiadascoisas/HotSpotAnalysis_Plugin">'
            'github.com/geografiadascoisas/HotSpotAnalysis_Plugin</a></p>'
        )

    # ------------------------------------------------------------------
    # Parameter declaration
    # ------------------------------------------------------------------

    def initAlgorithm(self, config=None):
        param = QgsProcessingParameterVectorLayer(
            self.INPUT, 'Input layer',
            types=[QgsProcessing.TypeVectorPoint,
                   QgsProcessing.TypeVectorPolygon],
        )
        param.setHelp('Point or polygon vector layer.')
        self.addParameter(param)

        param = QgsProcessingParameterField(
            self.FIELD, 'Analysis field',
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
        )
        param.setHelp('Numeric field containing the values to analyse. Features with NULL or NaN are automatically excluded (their output fields will be NaN).')
        self.addParameter(param)

        param = QgsProcessingParameterEnum(
            self.WEIGHTS_TYPE, 'Spatial weights type',
            options=self.WEIGHTS_OPTIONS,
            defaultValue=0,
        )
        param.setHelp('How neighbours are defined: Distance Band, KNN, or Queen Contiguity (polygons only).')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.THRESHOLD, 'Distance threshold (Distance Band)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=0.0,
        )
        param.setHelp('Maximum distance to consider a feature a neighbour (Distance Band). Leave empty to use the optimised value.')
        self.addParameter(param)

        param = QgsProcessingParameterBoolean(
            self.OPTIMIZE, 'Optimize threshold automatically',
            defaultValue=False,
        )
        param.setHelp('Finds the distance that maximises spatial autocorrelation within the Min / Max / Step range.')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.MIN_T, 'Minimum distance (optimization)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=0.0,
        )
        param.setHelp('Lower bound for automatic threshold optimisation.')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.MAX_T, 'Maximum distance (optimization)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=0.0,
        )
        param.setHelp('Upper bound for automatic threshold optimisation.')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.STEP_T, 'Step (optimization)',
            type=QgsProcessingParameterNumber.Double,
            optional=True, minValue=1.0,
        )
        param.setHelp('Increment step for automatic threshold optimisation.')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.KNN_K, 'K neighbors (KNN)',
            type=QgsProcessingParameterNumber.Integer,
            optional=True, minValue=1, defaultValue=5,
        )
        param.setHelp('Number of nearest neighbours (KNN only).')
        self.addParameter(param)

        param = QgsProcessingParameterBoolean(
            self.BINARY_WEIGHTS,
            'Binary weights (0/1) — unchecked = continuous (distance-decay)',
            defaultValue=True,
        )
        param.setHelp('Checked: neighbours count equally. Unchecked: weight decreases with distance.')
        self.addParameter(param)

        param = QgsProcessingParameterEnum(
            self.DISTANCE_METRIC, 'Distance metric',
            options=self.DISTANCE_OPTIONS,
            defaultValue=0,
        )
        param.setHelp('Formula used to measure distances between features.')
        self.addParameter(param)

        param = QgsProcessingParameterBoolean(
            self.ROW_STANDARDIZE, 'Row standardization',
            defaultValue=False,
        )
        param.setHelp('Normalises each row so weights sum to 1. Useful when features have unequal numbers of neighbours.')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PERMUTATIONS,
            'Random permutations (0 = normal approximation)',
            type=QgsProcessingParameterNumber.Integer,
            minValue=0, defaultValue=999,
        )
        param.setHelp('Monte Carlo simulations to compute the p-value. Default 999, following GeoDa and PySAL conventions (Anselin 1995; Ord &amp; Getis 1995). 0 = analytical approximation (faster but less robust).')
        self.addParameter(param)

        param = QgsProcessingParameterBoolean(
            self.TWO_TAILED,
            'Two-tailed p-value  (v1 compatibility — see help)',
            defaultValue=False,
        )
        param.setHelp('Compatibility with plugin v1 output. Not recommended; one-tailed is the standard.')
        self.addParameter(param)

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Local Moran's I output",
        ))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):
        try:
            from esda import Moran_Local, Moran
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

        if geom_type == QgsWkbTypes.PointGeometry and weights_type == 2:
            raise QgsProcessingException(
                "Queen's Contiguity requires a polygon layer."
            )

        if geom_type == QgsWkbTypes.PolygonGeometry and weights_type in (0, 1):
            feedback.pushWarning(
                "Distance-based weights for polygon layers use feature centroids, "
                "not polygon boundaries. For topology-based weights, consider "
                "Queen's Contiguity instead."
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

        # --- NaN guard (Caldas de Castro & Singer (2006); GeoDa convention) ---
        # esda uses y.mean() / y.std(), not nanmean — one NULL corrupts all.
        nan_mask = np.isnan(y)
        n_nan    = int(nan_mask.sum())
        if n_nan > 0:
            feedback.pushWarning(
                f"{n_nan} feature(s) with NULL/NaN in '{field_name}' will be "
                f"excluded from computation. Their result fields will be NaN."
            )
            valid  = ~nan_mask
            y      = y[valid]
            coords = [c for c, v in zip(coords, valid) if v]
        else:
            valid = np.ones(len(y), dtype=bool)

        n_valid = int(valid.sum())
        if n_valid < 3:
            raise QgsProcessingException(
                f"At least 3 valid features are required. "
                f"Only {n_valid} remain after excluding NULL/NaN values."
            )
        if y.std() == 0:
            raise QgsProcessingException(
                "Analysis field has zero variance. "
                "Local Moran's I requires variation in the values."
            )

        feedback.setProgress(10)

        # --- CRS warning for distance-based weights ---------------------
        if weights_type in (0, 1) and source.crs().isGeographic():
            feedback.pushWarning(
                "The layer CRS uses geographic coordinates (degrees). "
                "Distance Band and KNN thresholds will be in decimal degrees, "
                "not metric units. Consider reprojecting to a projected CRS "
                "before using distance-based weights."
            )

        # --- Spatial weights --------------------------------------------
        if weights_type == 2:
            # Build Queen weights from feature geometries via Shapely WKT.
            # Works with any QGIS vector provider (GeoPackage, PostGIS, memory,
            # filtered layers). Queen.from_shapefile() reads the full physical
            # file and ignores layer filters; from_iterable() builds from exactly
            # the valid features passed here, preserving NaN exclusions without
            # needing w_subset. Shapely is a mandatory dependency of libpysal.
            from shapely.wkt import loads as wkt_loads
            valid_geoms = [
                wkt_loads(d[0].geometry().asWkt())
                for d, v in zip(features_data, valid) if v
            ]
            w = Queen.from_iterable(valid_geoms)
            threshold_used = "Queen's Contiguity"

        elif weights_type == 1:
            knn_k = self.parameterAsInt(parameters, self.KNN_K, context)
            if knn_k >= n_valid:
                raise QgsProcessingException(
                    f"KNN requires k < number of valid features. "
                    f"Got k={knn_k}, valid features={n_valid}."
                )
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

        # --- Local Moran's I computation --------------------------------
        np.random.seed(12345)
        # n_jobs=1 is mandatory: joblib's loky backend cannot safely spawn
        # child processes inside QGIS (Qt environment + Windows FD conflict).
        statistics = Moran_Local(y, w, transformation=type_w,
                                 permutations=permutations, n_jobs=1)

        feedback.setProgress(75)

        from scipy.stats import norm as _norm
        use_perm   = permutations > 0 and hasattr(statistics, 'p_sim')
        two_tailed = self.parameterAsBoolean(parameters, self.TWO_TAILED, context)
        if use_perm:
            z_arr = statistics.z_sim
            p_arr = np.minimum(statistics.p_sim, 1.0 - statistics.p_sim)
        else:
            z_arr = statistics.z_norm
            p_arr = _norm.sf(np.abs(z_arr))
        if two_tailed:
            p_arr = np.minimum(p_arr * 2.0, 1.0)

        q_arr = getattr(statistics, 'q', None)

        p_fdr = fdr_bh(p_arr)
        if permutations == 0:
            feedback.pushInfo(
                'Note: FDR correction applied to analytical p-values. '
                'For more robust inference, consider setting permutations > 0.'
            )

        # Map results back to full feature array (NaN for excluded features)
        n_all     = len(features_data)
        z_out     = np.full(n_all, float('nan'))
        p_out     = np.full(n_all, float('nan'))
        p_fdr_out = np.full(n_all, float('nan'))
        z_out[valid]     = z_arr
        p_out[valid]     = p_arr
        p_fdr_out[valid] = p_fdr
        q_out = None
        if q_arr is not None:
            q_out = np.full(n_all, 0, dtype=int)
            q_out[valid] = q_arr

        # --- Build output -----------------------------------------------
        out_fields = QgsFields(source.fields())
        out_fields.append(QgsField('Z_score', QVariant.Double))
        out_fields.append(QgsField('p_value', QVariant.Double))
        out_fields.append(QgsField('q_value', QVariant.Int))
        out_fields.append(QgsField('p_fdr',   QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), source.sourceCrs(),
        )

        for i, (feat, _, _) in enumerate(features_data):
            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(feat.geometry())
            qval = int(q_out[i]) if q_out is not None and not nan_mask[i] else None
            out_feat.setAttributes(
                feat.attributes() + [float(z_out[i]), float(p_out[i]), qval, float(p_fdr_out[i])]
            )
            sink.addFeature(out_feat, QgsFeatureSink.FastInsert)

        feedback.setProgress(100)
        n_computed = int(valid.sum())
        feedback.pushInfo(
            f"Local Moran's I complete — {n_computed} features computed"
            + (f', {n_nan} excluded (NULL)' if n_nan > 0 else '')
            + f'  |  {threshold_used}'
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
        return MoranLocal()

    def tr(self, string):
        return string
