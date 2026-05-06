<p align="center">
  <img src="hotspot.png" alt="Hotspot Analysis Plugin" width="80">
</p>

# Hotspot Analysis v4: Geographical cluster detection

Modernized and maintained by **Abimael Cereda Junior**  
Email: **ceredajunior@geografiadascoisas.com.br**  
Repository: https://github.com/geografiadascoisas/HotSpotAnalysis_Plugin  
Issue tracker: https://github.com/geografiadascoisas/HotSpotAnalysis_Plugin/issues

---

## About this plugin

I am [Abimael Cereda Junior](https://www.linkedin.com/in/abimael-cereda-junior/)
- geographer, MSc and PhD in Urban Engineering, senior researcher at UnB and
professor in post-graduate programs. For 25 years I have been building Geographic
Intelligence operations: turning geoinformation into strategic decision-making
tools for clients like the World Bank, Sabesp, CPFL, Brazil's Ministry of
Social Development and UNDP. I founded
[Geografia das Coisas®](https://geografiadascoisas.com.br).

I say all this not to boast, but because it matters for understanding this
plugin: my background is spatial analysis and decision-making, not software
engineering. I have never thought of myself as a developer.

That said - I have been writing code since before my undergraduate degree.
Basic on a TK-85, Pascal and whatever came after. So perhaps a more honest
description is: I have always been a geographer who codes, even if I never
wore the developer hat officially.

This plugin has always been more about methodology than software. I use it in
my classes and consulting work to teach spatial statistics in a transparent,
reproducible way. For years I kept a private adapted version for teaching -
one that worked, but that I never felt confident enough to publish, partly
because I never thought of myself as a real developer.

The original plugin was developed by Daniele Oxoli et al. at Politecnico di
Milano in 2017. Over time, updates to Python libraries and QGIS itself broke
several parts of it - the plugin simply stopped working on QGIS 3.22 and
above. **Version 3** was a public release to bring it back to life: fixing
library compatibility, interface errors and basic stability. The calculations
themselves were not touched.

But something had always bothered me: even when it worked, the results did not
consistently match those from reference implementations. That methodological
discrepancy was the real motivation for going further.

**Version 4**, released in 2026 with the support of Claude Code, is a full
methodological revision - and the one that finally felt worth the effort of
doing properly. The calculations were reviewed step by step against Anselin's
LISA framework, correcting a silent error in the Gi* statistic (`star=True`
was missing) and fixing the p-value formula for cold spots. The plugin now
aligns with current community best practices and produces results consistent
with reference implementations.

The work with Claude Code accelerated the technical side considerably, but
always under close methodological oversight. Every calculation, every parameter
choice, every design decision was reviewed and validated by me. AI can help
write and organize code; it cannot replace the domain knowledge required to get
spatial statistics right.

The motivation was never just to rewrite the code. It was to make these tools
genuinely available to the whole community - working reliably across any
current or future version of QGIS, scientifically sound and open to everyone.

If you find errors or have questions, please open an issue on GitHub -
methodological questions especially welcome.

---

## Overview

Hotspot Analysis v4 is a QGIS plugin implementing **Local Indicators of Spatial Association (LISA)** using the Python libraries **libpysal** and **esda**. Version 4 migrates the plugin to the **QGIS Processing framework**, making all three algorithms available in the Processing Toolbox, the Graphical Modeler and batch processing - with no custom dialog required.

The plugin is designed to be **scientific and didactic**: all methodological choices are exposed as explicit parameters and this documentation explains the reasoning behind each one, aligned with the original references and GeoDa conventions.

Available in the QGIS **Processing Toolbox** under *Hotspot Analysis v4 → LISA*:

- **Getis-Ord Gi\***  
  Detection of significant hotspots (high–high clusters) and coldspots (low–low clusters).

- **Local Moran's I (univariate)**  
  Identification of local autocorrelation and spatial cluster/outlier patterns (HH, LL, HL, LH).

- **Local Moran's I (bivariate)**  
  Measures cross-variable local association between two spatial attributes.

The output layer includes:

- `Z_score`  
- `p_value`  
- `q_value` (for Moran's I only)  
- All original attributes preserved

---

## NEW in Version 4.0

- **Processing framework migration**: all three algorithms are now available in the QGIS Processing Toolbox, Graphical Modeler and Python console (`processing.run(…)`). No custom dialog.
- **Qt5/Qt6 compatible** via `qgis.PyQt` - works on QGIS 3.22+ and QGIS 4.x.
- **Scientific corrections** aligned with GeoDa and original references:
  - `G_Local` now uses `star=True` - the correct definition of Gi* (previously missing, causing Gi to be computed instead)
  - p-values use `1 − Φ(|Z|)` - one-tailed with absolute Z-score, consistent with Anselin (1995) and Ord & Getis (1995). The esda default `1 − Φ(Z)` (signed, directional) caused cold spots to be invisible; fixed. Optional **Two-tailed p-value** checkbox for v1/v3.x compatibility
- **New user parameters**:
  - **Binary vs continuous weights** (`binary=True/False`) - choose between binary (0/1) neighbourhood weights or continuous distance-decay weights
  - **Distance metric** - Euclidean (p=2, standard) or Manhattan (p=1, original danioxoli default)
- **Automatic threshold detection** using maximum nearest-neighbour distance (KDTree-based), applied when no threshold is provided
- Full scientific documentation in this README with formulas, parameter rationale and GeoDa alignment table

---

## NEW in Version 3.0.2

- Dependency Guard (blocking): the plugin now checks for required libraries (libpysal, esda) before starting. If missing, QGIS shows a clear message and the dialog does not open.
- Layer Guard (blocking): if the user clicks the plugin icon with no shapefile (.shp) vector layers loaded a message is displayed. The dialog will not open until the requirement is met.
- Cross-platform installation guidance: the plugin now provides system-appropriate instructions (Windows OSGeo4W, macOS app bundle Python, Linux package Python).
- Runtime stability improvements: hardened early-return logic; better detection of numeric fields; safer handling of NaN and missing values
- More explicit feedback to the user

---

## Key Improvements in Version 3.x

- Full migration from deprecated PySAL imports to **libpysal** and **esda**
- Rewritten and validated Z-score and p-value calculations for Gi\* and Moran
- Proper handling of q-values (Moran only)
- **KDTree-based** distance threshold estimation (with O(n²) fallback)
- Stable construction of:
  - Fixed Distance Band weights  
  - K-nearest neighbors (KNN)  
  - Queen contiguity weights
- Improved output layer writer with robust NaN handling
- Only numeric fields are offered for analysis
- Better stability on Windows (stdout/stderr guards)
- General code cleanup and removal of legacy logic

---

## Installation

### Plugin

Hotspot Analysis v4 can be installed in **two ways**:

1. **Directly from the official QGIS Plugin Repository** (recommended)  
2. **Manually via ZIP package** (for offline installation or unreleased versions)

#### 1. Install from the QGIS Plugin Repository (recommended)

Inside QGIS:

1. Open:
   ```
   Plugins → Manage and Install Plugins
   ```
2. Search for:
   ```
   Hotspot Analysis
   ```
3. Click:
   ```
   Install Plugin
   ```

#### 2. Install from ZIP (offline or development version)

1. Download the plugin ZIP package from the repository releases page.

2. In QGIS:
   ```
   Plugins → Install from ZIP
   ```

3. Enable the plugin:
   ```
   Plugins → Manage and Install Plugins → Hotspot Analysis
   ```

---

### Required Python Dependencies

Hotspot Analysis v4 requires the libraries:

```
libpysal
esda
```

If these libraries are missing, the plugin will show a dependency error when any algorithm is run.

#### Windows (QGIS 4.x - OSGeo4W Shell)
```
python -m pip install libpysal esda
```

> **Recommended:** QGIS 4.x will automatically prompt you to install the required
> dependencies (`libpysal`, `esda`) when the plugin is first activated, via the
> `pip_dependencies` mechanism built into the QGIS Plugin Manager.
> Manual installation is only needed if the automatic prompt does not appear.

#### macOS (QGIS bundled Python)
```
/Applications/QGIS.app/Contents/MacOS/bin/python3 -m pip install libpysal esda
```

#### Linux
```
python3 -m pip install libpysal esda
```

---

### Troubleshooting: `Numba needs NumPy 2.3 or less`

QGIS 4.x ships with **NumPy 2.4+**. If `numba` is installed in your Python
environment at a version that only supports NumPy ≤ 2.3, `libpysal` will fail
to load (even though you did not ask for numba - `libpysal` imports it
internally via `Gabriel` weights).

**Fix - open the OSGeo4W Shell and run:**
```
python -m pip install --upgrade numba
```

Numba 0.62+ supports NumPy 2.4. If the upgrade is not yet available for your
platform, an alternative is to pin an older libpysal that predates the Gabriel
dependency:
```
python -m pip install "libpysal<4.10" esda
```

---

### Optional: SciPy Optimization (KDTree)

If SciPy is available, the plugin automatically uses KDTree for optimized spatial distance computations.

To install (optional):
```
pip install scipy
```

If SciPy is not installed, the plugin uses a safe O(n²) fallback.

---

### Requirements Before Running the Plugin

To execute any hotspot or LISA analysis, you must:

- Load **at least one shapefile (.shp)**  
- Use **point** or **polygon** geometry  
- Ensure the layer is in a **projected CRS** (meters, not degrees)  
- Have at least one **numeric attribute field**

---

## Methodology

### 1. Getis-Ord Gi*

**References:** Getis & Ord (1992); Ord & Getis (1995)

The Gi* statistic measures spatial concentration of a variable by comparing the local sum of values within a neighbourhood against the global sum. A positive and significant Z-score indicates a spatial cluster of high values (hot spot); a negative and significant Z-score indicates a cluster of low values (cold spot).

**Formula:**

```
        Σ_j w*_ij x_j  −  x̄ Σ_j w*_ij
Gi* = ─────────────────────────────────────────────────────────────
      s × √[ (n Σ_j w*²_ij − (Σ_j w*_ij)²) / (n−1) ]
```

where `w*_ij` are the spatial weights **including the diagonal** (location i is its own neighbour), `x̄` is the global mean, `s` is the global standard deviation and `n` is the number of observations.

**Gi vs Gi\*:** The non-starred Gi excludes location i from its own weighted sum (zero diagonal). The Gi\* includes it (`star=True`). This plugin always computes **Gi\***, which is the form implemented in GeoDa and ArcGIS and the form most commonly reported in the literature.

---

### 2. Local Moran's I

**Reference:** Anselin (1995)

The Local Moran's I decomposes the global Moran's I into a contribution per location, identifying statistically significant spatial clusters (similar values) and spatial outliers (dissimilar values).

**Formula:**

```
I_i = z_i Σ_j w_ij z_j
```

where `z_i = (x_i − x̄) / s` is the standardised value at location i.

**Quadrant classification (q_value):**

| Code | Label | Meaning |
|---|---|---|
| 1 | **HH** | High–High: cluster of high values |
| 2 | **LH** | Low–High: low value surrounded by high values (outlier) |
| 3 | **LL** | Low–Low: cluster of low values |
| 4 | **HL** | High–Low: high value surrounded by low values (outlier) |

---

### 3. Bivariate Local Moran's I

**References:** Anselin et al. (2002); Anselin (1995)

Measures the association between variable X at location i and the **spatial lag of variable Y** across neighbouring locations j:

```
I_i^B = z_x_i Σ_j w_ij z_y_j
```

**Methodological note - what this statistic does NOT measure:**

The Bivariate Local Moran does **not** measure whether X and Y co-occur at the same location i. It measures whether a high (or low) value of X at i is surrounded by high (or low) values of Y at its neighbours. Always complement the bivariate analysis with univariate analyses of each variable. This limitation is explicitly noted in Anselin et al. (2002) and in GeoDa's documentation.

---

## Parameters

### Spatial weights type

| Option | When to use |
|---|---|
| **Distance Band** | Point layers - all points within the threshold distance are neighbours |
| **KNN** | Point layers - each point has exactly K neighbours (useful when density is uneven) |
| **Queen's Contiguity** | Polygon layers - polygons sharing an edge or a vertex are neighbours |

Queen's Contiguity is automatically selected for polygon layers regardless of the user's choice.

### Distance threshold (Distance Band)

The minimum distance that ensures every point has at least one neighbour. If left blank, the plugin computes this automatically as the maximum nearest-neighbour distance across all points (Ord & Getis 1995, recommended practice).

### Optimize threshold automatically

Tests all thresholds between *Minimum distance* and *Maximum distance* at the given *Step* and selects the one that maximises the global Moran's I z-score. Computationally intensive for large datasets.

### Binary weights (0/1)

| Setting | Effect |
|---|---|
| **Checked (binary=True)** | All neighbours within the threshold receive weight 1; all others receive 0. GeoDa default for distance bands. |
| **Unchecked (binary=False)** | Weights decay with distance (continuous). More faithful to the original theoretical formulation of Getis & Ord (1992). The original danioxoli plugin used this setting. |

Both options are scientifically valid - the choice should reflect the research hypothesis.

### Distance metric

| Option | Parameter | When to use |
|---|---|---|
| **Euclidean (p=2)** | Standard straight-line distance | Default for geographic data in projected CRS. GeoDa default. |
| **Manhattan (p=1)** | Sum of absolute differences in each axis | Grid-like urban street networks. Original danioxoli default. |

### Row standardization

Divides each weight by the row sum so all rows sum to 1. Removes the effect of varying neighbourhood sizes, allowing comparison across locations. Recommended when neighbourhood sizes vary significantly.

### Random permutations

| Value | Effect |
|---|---|
| **0** | Normal approximation (analytic p-value; fast) |
| **999** | Default for Moran statistics; recommended by Anselin (1995) |
| **9999** | Higher precision; use for publication-quality results |

For Getis-Ord Gi*, the default is 0 (normal approximation), consistent with GeoDa.

---

## P-values

### Formula

The plugin computes p-values as **one-tailed using the absolute value of the Z-score**:

```
p = 1 − Φ(|Z|)
```

where Φ is the standard normal CDF. This is the formulation used in the primary spatial analysis references (Anselin 1995; Ord & Getis 1995) and in standard implementations of these statistics.

| |Z| | p (one-tailed \|Z\|) | Confidence level |
|---|---|---|
| ≥ 1.65 | ≤ 0.050 | 90% |
| ≥ 1.96 | ≤ 0.025 | 95% |
| ≥ 2.58 | ≤ 0.005 | 99% |

### Why |Z|, not the signed Z?

Using the raw signed Z in `1 − Φ(Z)` gives a **directional** p-value:

- For hot spots (Z > 0): `1 − Φ(Z)` → small → correctly identified as significant
- For cold spots (Z < 0): `1 − Φ(Z)` → close to 1 → cold spots **never appear significant**

This is methodologically wrong: a cold spot at Z = −2.58 is just as statistically significant as a hot spot at Z = +2.58. Using `1 − Φ(|Z|)` treats both directions correctly and symmetrically. The **direction** of the cluster (hot or cold) is already encoded in the sign of the Z_score - p_value is the measure of significance, not of direction.

The esda library returns `1 − Φ(Z)` (signed) for `G_Local.p_norm`, which incorrectly renders cold spots invisible in the default output layer style. This plugin overrides that calculation to use `1 − Φ(|Z|)` consistently for all three statistics.

### Default QML classification

The default output style classifies features using **p_value as the primary significance criterion** and **sign(Z_score) as the secondary direction criterion**. This approach follows GeoDa and the original references: p_value measures whether the association is statistically significant; the sign of Z_score identifies the direction (hot or cold cluster).

| Condition | Label |
|---|---|
| Z_score < 0 AND p_value ≤ 0.005 | coldspot 99% confidence |
| Z_score < 0 AND 0.005 < p_value ≤ 0.025 | coldspot 95% confidence |
| Z_score < 0 AND 0.025 < p_value ≤ 0.050 | coldspot 90% confidence |
| p_value > 0.050 | not significant |
| Z_score > 0 AND 0.025 < p_value ≤ 0.050 | hotspot 90% confidence |
| Z_score > 0 AND 0.005 < p_value ≤ 0.025 | hotspot 95% confidence |
| Z_score > 0 AND p_value ≤ 0.005 | hotspot 99% confidence |

Under the normal approximation with `1 − Φ(|Z|)`, the p_value thresholds correspond exactly to the Z_score ranges |Z| ≥ 1.65 (90%), ≥ 1.96 (95%), ≥ 2.58 (99%). With permutation-based p-values the two can diverge, making the p_value-primary approach the only correct one for both modes.

### Two-tailed option (v1 compatibility)

Checking **Two-tailed p-value** doubles the default p:

```
p_two = min(2 × p, 1.0)
```

This replicates v3.x/v1 plugin behavior and also matches the convention used by a major commercial GIS implementation. Use this option to compare outputs with v3.x results or with external analyses computed with two-tailed p-values. One-tailed remains the recommended default.

> **Note for users of v3.x:** v3.x applied a two-tailed conversion using the *signed* Z-score (`p_norm * 2`, where `p_norm = 1 − Φ(Z)`), which caused cold spots to receive p ≈ 1.0 and disappear from the output style. v4.0 corrects this: uses `1 − Φ(|Z|)` so hot and cold spots are treated symmetrically and classifies features by p_value (primary) + sign(Z_score) (direction), aligned with GeoDa and Anselin (1995).

---

## Alignment with GeoDa and original references

| Aspect | GeoDa | This plugin (v4) |
|---|---|---|
| Gi* variant | star=True | star=True ✓ |
| P-value direction | one-tailed | one-tailed ✓ |
| Distance band default | binary=True | binary=True ✓ (configurable) |
| KNN distance | Euclidean (p=2) | Euclidean ✓ (configurable) |
| Row standardization | optional | optional ✓ |
| Quadrants HH/LH/LL/HL | 1/2/3/4 | 1/2/3/4 ✓ |
| Computation engine | C++ (GeoDa) | libpysal/esda (PySAL) |

The libpysal/esda library is maintained by the **PySAL developers network**, which shares the same scientific lineage as GeoDa (both rooted in Luc Anselin's work at the GeoDa Center). The formulas are identical; only the implementation language differs.

---

## Implementation Audit: v1, GeoDa, ArcGIS and the Literature

This section documents a systematic comparison of implementation choices across four reference points: the original danioxoli plugin (v1/v3.x), GeoDa 1.22, ArcGIS Pro 3.x and the scientific literature (Anselin 1995; Ord & Getis 1995). The audit drove all corrections introduced in v4 and is provided here so that results can be independently reproduced and compared.

---

### Full comparison table (Getis-Ord Gi*)

| Aspect | Literature | danioxoli v1/v3.x | GeoDa 1.22 | ArcGIS Pro 3.x | **This plugin (v4)** |
|---|---|---|---|---|---|
| Gi* variant (`star`) | `star=True` [1] | `star=False` ✗ | `star=True` ✓ | `star=True` ✓ | `star=True` ✓ |
| p-value formula | `1 − Φ(\|Z\|)` [1][2] | `(1 − Φ(Z)) × 2` ✗ | `1 − Φ(\|Z\|)` ✓ | `2 × (1 − Φ(\|Z\|))` | `1 − Φ(\|Z\|)` ✓ |
| Z-score sign flip | None | `if mean(y) ≤ 0: Z ← −Z` ✗ | None | None | None ✓ |
| Weight type default | Binary [1] | `binary=False` (continuous) | `binary=True` ✓ | Binary | `binary=True` ✓ (configurable) |
| Distance metric | Euclidean | Manhattan (p=1) | Euclidean | Euclidean | Euclidean ✓ (configurable) |
| Map classification | p_value primary [1][2] | Z-score ranges only | p_value primary ✓ | Z-score ranges (≡ two-tailed p) | p_value primary ✓ |
| Output field names | - | `Z-score`, `p-value` (hyphens) ✗ | - | - | `Z_score`, `p_value` (underscores) ✓ |

For Local Moran's I the same p-value and classification principles apply. The `q_value` quadrant encoding (1=HH, 2=LH, 3=LL, 4=HL) matches GeoDa and Anselin (1995) in all versions.

---

#### Note on `binary=False` (continuous weights)

The original plugin used `DistanceBand(coords, threshold=d, binary=False)`, applying distance-decay weights instead of the binary 0/1 weights used by GeoDa and most published applications. This is not incorrect - continuous weights are consistent with the theoretical formulation of Getis & Ord (1992) - but it diverges from the GeoDa default without documentation and produces different numerical results. In v4, `binary=True` is the default (GeoDa convention) but the choice is exposed as an explicit parameter so users can replicate either behavior.

---

### Why p_value primary is scientifically mandatory for permutation tests

Both ArcGIS (Z-score ranges) and v1 (Z-score × 2) imply classification by Z magnitude. Under the **normal approximation**, classifying by |Z| ≥ 1.96 and by analytic p ≤ 0.025 are mathematically equivalent, so the distinction appears cosmetic.

However, with **permutation-based p-values** the two diverge: a feature may have |Z| ≥ 1.96 under the analytic normal distribution but `p_sim > 0.025` under the empirical permutation distribution (or vice versa). In that case, using the Z magnitude classification ignores the permutation test result and produces misleading output.

Because this plugin supports permutation-based p-values (via `esda`), the only scientifically correct approach is to classify by **p_value** (whether analytic or permutation) with the sign of Z_score as the secondary direction criterion. This is the approach implemented in GeoDa and described in Anselin (1995, p. 103).

---

### p-value threshold correspondence table

Under `1 − Φ(|Z|)` (this plugin default and GeoDa convention):

| |Z| threshold | p_value threshold | Confidence level | Label |
|---|---|---|---|---|
| |Z| ≥ 1.645 | p ≤ 0.050 | 90% | hotspot/coldspot 90% confidence |
| |Z| ≥ 1.960 | p ≤ 0.025 | 95% | hotspot/coldspot 95% confidence |
| |Z| ≥ 2.576 | p ≤ 0.005 | 99% | hotspot/coldspot 99% confidence |

Under `2 × (1 − Φ(|Z|))` (ArcGIS two-tailed convention):

| |Z| threshold | two-tailed p threshold | ArcGIS label |
|---|---|---|---|
| |Z| ≥ 1.645 | p ≤ 0.100 | 90% confidence |
| |Z| ≥ 1.960 | p ≤ 0.050 | 95% confidence |
| |Z| ≥ 2.576 | p ≤ 0.010 | 99% confidence |

The **Two-tailed p-value** option in v4 (`p × 2`) replicates the ArcGIS/v3.x behavior and shifts p_value thresholds accordingly.

---

### References for this audit

[1] Ord, J.K. & Getis, A. (1995). *Local Spatial Autocorrelation Statistics: Distributional Issues and an Application*. Geographical Analysis, 27(4), 286–306. - defines Gi*, p-value as `1 − Φ(|Z|)` and binary distance-band weights as the standard form.

[2] Anselin, L. (1995). *Local Indicators of Spatial Association - LISA*. Geographical Analysis, 27(2), 93–115. - defines significance classification by p-value threshold and cluster direction by sign of the local statistic.

[3] GeoDa 1.22 documentation: https://geodacenter.github.io/workbook/6a_local_auto/lab6a.html - demonstrates p_value-primary classification with `1 − Φ(|Z|)`.

[4] ArcGIS Pro 3.x documentation - *Hot Spot Analysis (Getis-Ord Gi*)* - uses two-tailed p and classifies by Z_score ranges. Numerically equivalent to one-tailed classification under the normal approximation but diverges for permutation p-values.

[5] Oxoli, D., Prestifilippo, G., Bertocchi, D., Zurbaràn, M. (2017). *Enabling spatial autocorrelation mapping in QGIS: The Hotspot Analysis Plugin*. GEAM, 151(2), 45–50. - original publication of the danioxoli plugin (v1).

[6] esda library - `G_Local.p_norm` returns `1 − Φ(Z)` with signed Z (directional). This plugin overrides it with `scipy.stats.norm.sf(np.abs(z_arr))` to use `1 − Φ(|Z|)` as in [1][2][3].

---

## Output Fields

| Field | Description |
|---|---|
| `Z_score` | Standardized measure of local association |
| `p_value` | One-tailed significance value (aligned with GeoDa; see *P-values* section) |
| `q_value` | Moran quadrant: 1=HH, 2=LH, 3=LL, 4=HL (Moran algorithms only) |

---

## References

**Statistical Foundations**  
- Getis, A.; Ord, J.K. (1992). *The Analysis of Spatial Association by Use of Distance Statistics*. Geographical Analysis, 24(3), 189–206.  
- Getis, A.; Ord, J.K. (1996). *Local Spatial Statistics: An Overview*. In Longley & Batty (Eds.), Spatial Analysis: Modelling in a GIS Environment.  
- Anselin, L. (1995). *Local Indicators of Spatial Association - LISA*. Geographical Analysis, 27(2), 93–115.  
- Wartenberg, D. (1985). *Multivariate Spatial Correlation: A Method for Exploratory Geographical Analysis*. Geographical Analysis, 17(4), 263–283.  
- Anselin, L., Syabri, I. & Smirnov, O. (2002). *Visualizing Multivariate Spatial Correlation with Dynamically Linked Windows*. In Anselin & Rey (Eds.), New Tools for Spatial Data Analysis. CSISS.  

**Methodological Background**  
- de Smith, M., Goodchild, M., Longley, P. (2015). *Geospatial Analysis* (5th edition).  
- Rey, S.J. & Anselin, L. (2010). *PySAL: A Python Library of Spatial Analytical Methods*. In Fischer & Getis (Eds.), Handbook of Applied Spatial Analysis. Springer.

**Original Plugin Citation**  
_Oxoli, D., Prestifilippo, G., Bertocchi, D., Zurbaràn, M. (2017).  
Enabling spatial autocorrelation mapping in QGIS: The Hotspot Analysis Plugin.  
GEAM. GEOINGEGNERIA AMBIENTALE E MINERARIA, 151(2), 45–50._

---

## Additional Material

An user guide with demo exercises is included here: https://github.com/danioxoli/HotSpotAnalysis_Plugin/blob/master/test_data/Hotspot_Analysis_UserGuide.pdf

Latest presentation available here: http://www.slideshare.net/danieleoxoli/hotspot-analysis-with-qgis-foss4git-2017

**Note**: part of this material is based on earlier versions of the plugin and may not reflect the current Processing-based interface.

---

## Future work

- Improve and update the User Guide for Processing-based interface
- Add support for additional spatial weights types
- Add batch processing examples and model templates
- Explore integration with additional libpysal statistics

---

## License

_The Hotspot Analysis plugin is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation._

Copyright © 2026 Abimael Cereda Junior - [Geografia das Coisas]  
Copyright © 2021 Daniele Oxoli - [Politecnico Di Milano] | Gabriele Prestifilippo - [GISdevio]

E-mail (maintainer): ceredajunior@geografiadascoisas.com.br  
E-mail (original author): daniele.oxoli@polimi.it

___

 [GISdevio]: <https://gisdev.io/en?lang=en>
 [Politecnico Di Milano]: <https://www.polimi.it/>
 [Geografia das Coisas]: <https://github.com/geografiadascoisas>
 [PySAL]: <https://pysal.org/>
 [Getis and Ord, 1992]: <http://onlinelibrary.wiley.com/doi/10.1111/j.1538-4632.1992.tb00261.x/full>
 [Geospatial Analysis - 5th Edition, 2015 - de Smith, Goodchild, Longley]: <http://www.spatialanalysisonline.com/HTML/index.html?local_indicators_of_spatial_as.htm>
 [OSGeo4W Shell]:<http://trac.osgeo.org/osgeo4w/>
 [Getis and Ord, 1996]: <http://onlinelibrary.wiley.com/doi/10.1111/j.1538-4632.1995.tb00912.x/pdf>
 [Anselin, 1995]: <http://onlinelibrary.wiley.com/store/10.1111/j.1538-4632.1995.tb00338.x/asset/j.1538-4632.1995.tb00338.x.pdf;jsessionid=A8B95BCA3E3DAFED243732CC66B31B63.f02t01?v=1&t=j0hvb8t7&s=c3f30861dca953c035e5b1dbbc24ea6b659a82c5>
 [Wartenberg, 1985]:<http://onlinelibrary.wiley.com/store/10.1111/j.1538-4632.1985.tb00849.x/asset/j.1538-4632.1985.tb00849.x.pdf?v=1&t=j0uyit1b&s=7ad70b665f08164ec74068d58eedf6f65e072dfa>
 [Anselin et al., 2002]:<https://pdfs.semanticscholar.org/4e34/bd70317377971ba8df7259288b972ad6a239.pdf>
 [previous version here]:<https://github.com/danioxoli/HotSpotAnalysis_Plugin/tree/qgis3>
 [here]:<https://www.youtube.com/watch?v=lnDkbdKKJXM&ab_channel=AMDGS>
