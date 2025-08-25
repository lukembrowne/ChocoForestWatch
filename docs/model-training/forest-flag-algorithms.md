# Forest Flag Algorithm Documentation

This document provides detailed information about the forest flag generation algorithms available in the ChocoForestWatch ML pipeline.

## Overview

Forest flag algorithms determine how monthly prediction data is combined into annual forest/non-forest classifications. Each algorithm handles temporal patterns differently, making them suitable for different monitoring objectives.

## Algorithm Descriptions

### 1. Majority Vote (`majority_vote`)

**Description**: Uses the most frequent class across all valid monthly observations.

**How it works**:
- Counts occurrences of forest (0), non-forest (1), and water (4) classes
- Selects the class with the highest count
- Ignores cloud, shadow, haze, sensor error, and no-data pixels

**Example**:
```
Time series: [Forest, Forest, Non-Forest, Forest] → Forest (3 vs 1)
Time series: [Forest, Forest, Non-Forest, Non-Forest] → Tie → Forest (argmax behavior)
```

**Strengths**:
- Simple and predictable
- Works well for stable land cover areas
- Computationally efficient
- Provides consistent baseline performance

**Limitations**:
- **Misses temporal patterns**: Cannot detect deforestation that occurs later in the year
- **Ignores sequence**: A pixel changing from forest to non-forest may still be classified as forest if forest observations are more frequent

**Best for**:
- Stable forest areas
- Baseline performance comparisons
- Areas with consistent land cover

**Data requirements**: 2+ valid monthly observations

### 2. Temporal Trend (`temporal_trend`) - **Recommended**

**Description**: Analyzes temporal sequence patterns to detect genuine land cover changes while filtering noise.

**How it works**:
1. **Recent Consensus**: If last 2-3 observations are consistent, use that classification
2. **Change Point Detection**: Identifies forest→non-forest transitions
3. **Run Length Analysis**: Filters out isolated classifications (likely noise)
4. **Majority Fallback**: Uses majority vote if no clear temporal pattern exists

**Example**:
```
[Forest, Forest, Forest, Non-Forest] → Non-Forest (deforestation detected)
[Forest, Non-Forest, Forest, Forest] → Forest (isolated noise filtered)
[Non-Forest, Non-Forest, Forest, Forest] → Forest (reforestation detected)
[Non-Forest, Forest, Non-Forest, Non-Forest] → Non-Forest (isolated forest filtered)
```

**Strengths**:
- **Excellent deforestation detection**: Correctly identifies late-season forest loss
- **Noise filtering**: Removes isolated misclassifications
- **Pattern recognition**: Understands temporal sequences
- **Balanced approach**: Considers both recent and historical data

**Limitations**:
- Requires more valid observations for optimal performance
- Slightly more complex than majority vote
- May be sensitive to parameter tuning

**Best for**:
- **Deforestation monitoring** (primary use case)
- Areas with temporal land cover changes
- Noise-prone environments
- Operational forest monitoring

**Data requirements**: 3+ valid monthly observations

### 3. Change Point Detection (`change_point`)

**Description**: Uses statistical methods to identify significant transitions in time series data.

**How it works**:
1. **Segmentation**: Tests different time points as potential change points
2. **Statistical Analysis**: Calculates confidence scores for each potential change point
3. **Significance Testing**: Only accepts change points above confidence threshold (0.6)
4. **Post-change Classification**: Uses the dominant class after the most significant change point
5. **Deforestation Bonus**: Applies 1.2x weight to forest→non-forest transitions

**Example**:
```
[Forest, Forest, Non-Forest, Non-Forest] → Non-Forest (significant change at position 2)
[Forest, Non-Forest, Forest, Non-Forest] → Majority vote (no significant change point)
```

**Strengths**:
- **Statistical rigor**: Uses confidence scoring for change detection
- **Robust to noise**: Requires statistical significance for changes
- **Prioritizes deforestation**: Weighted scoring for forest loss
- **Interpretable results**: Provides confidence metrics

**Limitations**:
- Requires more data points for statistical significance
- May miss subtle changes below confidence threshold
- More computationally intensive

**Best for**:
- Areas with clear land cover transitions
- Statistical analysis and reporting
- High-confidence change detection
- Research applications

**Data requirements**: 4+ valid monthly observations

### 4. Latest Valid (`latest_valid`)

**Description**: Uses the most recent valid observation as the final classification.

**How it works**:
- Finds the last non-masked observation in the time series
- Directly uses that observation as the final classification
- Very simple and direct approach

**Example**:
```
[Forest, Forest, Non-Forest, Forest] → Forest (last valid observation)
[Forest, Non-Forest, Cloud, Non-Forest] → Non-Forest (last valid observation)
```

**Strengths**:
- **Maximum sensitivity**: Detects the most recent changes
- **Simple implementation**: Easy to understand and debug
- **Low data requirements**: Only needs one valid observation
- **Real-time monitoring**: Reflects current conditions

**Limitations**:
- **Highly noise-sensitive**: Single misclassified pixel affects entire result
- **Ignores historical context**: No consideration of past patterns
- **Prone to false positives**: May classify temporary changes as permanent

**Best for**:
- Real-time monitoring applications
- Areas with reliable recent data
- Rapid change detection
- Situations where latest state is most important

**Data requirements**: 1+ valid monthly observation

### 5. Weighted Temporal (`weighted_temporal`)

**Description**: Applies exponential decay weighting to favor recent observations while considering historical data.

**How it works**:
1. **Weight Calculation**: Applies exponential decay weights (e^(-0.3 * distance_from_end))
2. **Weighted Voting**: Counts each observation weighted by its temporal distance
3. **Balanced Decision**: Recent observations have higher influence but historical data still matters

**Example**:
```
[Forest, Forest, Non-Forest, Non-Forest] → Non-Forest (recent observations weighted higher)
Weights: [0.41, 0.55, 0.74, 1.0] → Recent non-forest observations dominate
```

**Strengths**:
- **Balanced approach**: Considers both recent and historical patterns
- **Smooth weighting**: Gradual rather than abrupt temporal weighting
- **Flexible**: Can detect both recent changes and stable patterns
- **Moderate sensitivity**: Less prone to noise than latest_valid

**Limitations**:
- **Parameter dependency**: Exponential decay rate affects results
- **Complex interpretation**: Weighting scheme may be less intuitive
- **Moderate performance**: Not optimized for specific use cases

**Best for**:
- General-purpose monitoring
- Areas with mixed temporal patterns
- Balanced change detection
- Situations requiring both recent and historical context

**Data requirements**: 2+ valid monthly observations

## Performance Comparison

Based on synthetic test data with known patterns:

| Test Case | Pattern | Majority Vote | Temporal Trend | Change Point | Latest Valid | Weighted Temporal |
|-----------|---------|---------------|----------------|--------------|--------------|-------------------|
| Deforestation | `[F,F,F,N]` | Forest | **Non-Forest** | **Non-Forest** | **Non-Forest** | Forest |
| Stable Forest | `[F,F,F,F]` | **Forest** | **Forest** | **Forest** | **Forest** | **Forest** |
| Stable Non-Forest | `[N,N,N,N]` | **Non-Forest** | **Non-Forest** | **Non-Forest** | **Non-Forest** | **Non-Forest** |
| Noise in Forest | `[F,N,F,F]` | **Forest** | **Forest** | **Forest** | **Forest** | **Forest** |
| Noise in Non-Forest | `[N,F,N,N]` | **Non-Forest** | **Non-Forest** | **Non-Forest** | **Non-Forest** | **Non-Forest** |
| Reforestation | `[N,N,F,F]` | **Forest** | **Forest** | **Forest** | **Forest** | **Forest** |
| Mixed Recent | `[F,F,N,N]` | Forest | **Non-Forest** | **Non-Forest** | **Non-Forest** | **Non-Forest** |
| Late Deforestation | `[F,F,F,N,N]` | Forest | **Non-Forest** | **Non-Forest** | **Non-Forest** | Forest |

**Legend**: F=Forest, N=Non-Forest; **Bold** = Expected/Correct Result

## Algorithm Selection Guidelines

### For Deforestation Monitoring
**Recommended**: `temporal_trend`
- Best performance for detecting forest loss
- Filters noise effectively
- Handles late-season deforestation

### For Statistical Analysis
**Recommended**: `change_point`
- Provides confidence metrics
- Statistically rigorous approach
- Good for research applications

### For Real-time Monitoring
**Recommended**: `latest_valid`
- Maximum sensitivity to recent changes
- Simple interpretation
- Low computational requirements

### For Stable Areas
**Recommended**: `majority_vote`
- Reliable baseline performance
- Computationally efficient
- Good for consistent land cover

### For General Purpose
**Recommended**: `weighted_temporal`
- Balanced approach
- Moderate sensitivity
- Good compromise between approaches

## Technical Implementation Notes

### Data Handling
- All algorithms automatically filter invalid observations (cloud, shadow, haze, sensor error, no-data)
- Minimum valid observation requirements vary by algorithm
- Pixels with insufficient data are set to 255 (no-data)

### Processing Efficiency
- `majority_vote` and `latest_valid`: Fastest processing
- `temporal_trend` and `weighted_temporal`: Moderate processing time
- `change_point`: Slower due to statistical calculations

### Memory Usage
- All algorithms use vectorized operations for efficiency
- Memory usage scales with image size, not temporal complexity
- Processing is done pixel-by-pixel to handle large datasets

## Usage Examples

### Command Line Usage
```bash
# Basic usage with temporal trend
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --run_id "deforestation_monitoring" \
  --forest-algorithm temporal_trend

# Change point detection for research
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --run_id "change_analysis" \
  --forest-algorithm change_point

# Real-time monitoring
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --run_id "monitoring_2022" \
  --forest-algorithm latest_valid
```

### Programmatic Usage
```python
from ml_pipeline.composite_generator import CompositeGenerator

# Initialize generator
with CompositeGenerator(run_id="test", year="2022") as generator:
    # Generate composite with temporal trend algorithm
    forest_flag = generator.generate_composite(
        quad_name="567-1027",
        algorithm="temporal_trend"
    )
```

## Best Practices

1. **Start with temporal_trend**: Best general-purpose algorithm for most use cases
2. **Validate with test data**: Use synthetic time series to understand algorithm behavior
3. **Consider data quality**: Algorithms requiring more observations perform better with consistent data
4. **Monitor performance**: Compare results across algorithms for your specific area
5. **Document choices**: Record which algorithm was used for reproducibility

## Troubleshooting

### Common Issues
- **No-data results**: Ensure sufficient valid monthly observations
- **Unexpected classifications**: Check for noise in input data
- **Performance issues**: Consider using majority_vote for large-scale processing

### Debugging Tips
- Use the test script to validate algorithm behavior on synthetic data
- Check log output for algorithm selection confirmation
- Verify input data quality and temporal coverage

## Future Enhancements

Planned improvements include:
- Adaptive parameter tuning based on data characteristics
- Integration with confidence metrics for all algorithms
- Performance optimization for large-scale processing
- Additional algorithms for specific use cases

## References

- [Composite Generation Implementation](../../ml_pipeline/src/ml_pipeline/composite_generator.py)
- [Algorithm Test Script](../../ml_pipeline/notebooks/test_forest_algorithms.py)
- [Main README](../../README.md#forest-flag-algorithm-selection)