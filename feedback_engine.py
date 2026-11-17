from collections import Counter
from statistics import median, StatisticsError, mode

import numpy as np


def process_feedback(feedbacks):
    """Aggregate fare feedback into a community estimate with confidence scoring."""
    if not feedbacks:
        return None

    fares = [float(f.fare) for f in feedbacks if f and f.fare is not None]
    if not fares:
        return None

    total = len(fares)
    if total < 2:
        return {
            'mode': fares[0],
            'median': fares[0],
            'mean': fares[0],
            'frequency': 1,
            'total': total,
            'confidence_score': 0.25,
            'confidence_label': 'Low',
            'distribution': [
                {'fare': round(fares[0], 2), 'count': 1}
            ],
            'suspicious': False,
        }

    # Remove duplicates and obvious outliers using IQR-based filtering.
    unique_fares = sorted(set(round(f, 2) for f in fares))
    if len(unique_fares) > 1:
        q75, q25 = np.percentile(unique_fares, [75, 25])
        iqr = q75 - q25
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr
        filtered = [fare for fare in unique_fares if lower_bound <= fare <= upper_bound]
        if filtered:
            unique_fares = filtered

    if not unique_fares:
        return None

    fare_counts = Counter(round(fare, 2) for fare in unique_fares)
    try:
        most_frequent = mode(list(fare_counts.elements()))
    except StatisticsError:
        most_frequent = sorted(fare_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]

    frequency = fare_counts.get(most_frequent, 0)
    mean_fare = sum(unique_fares) / len(unique_fares)
    median_fare = median(unique_fares)
    confidence = frequency / len(unique_fares)

    if confidence >= 0.7:
        confidence_label = 'High'
    elif confidence >= 0.4:
        confidence_label = 'Medium'
    else:
        confidence_label = 'Low'

    distribution = [
        {'fare': float(fare), 'count': count}
        for fare, count in sorted(fare_counts.items())
    ]

    suspicious = any(fare < 2 or fare > 1000 for fare in unique_fares)

    return {
        'mode': float(most_frequent),
        'median': float(median_fare),
        'mean': float(mean_fare),
        'frequency': frequency,
        'total': total,
        'confidence_score': round(float(confidence), 4),
        'confidence_label': confidence_label,
        'distribution': distribution,
        'suspicious': suspicious,
    }