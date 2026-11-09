"""Evaluate condition predictions on held-out examples, never fit a model here."""
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def evaluate(actual, probabilities, labels):
    predicted = np.array(labels)[np.argmax(probabilities, axis=1)]
    return {'accuracy': float(accuracy_score(actual, predicted)),
            'report': classification_report(actual, predicted, labels=labels, output_dict=True, zero_division=0),
            'confusion_matrix': confusion_matrix(actual, predicted, labels=labels).tolist(),
            'test_rows': len(actual)}

