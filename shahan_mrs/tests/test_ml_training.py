"""Regression checks for holdout isolation, family weighting and metric labels."""
import unittest

import numpy as np

from src.ml.condition_training import calculate_training_weights, split_dataset
from src.ml.evaluation import evaluate


class TrainingWorkflowTests(unittest.TestCase):
    def test_fixed_holdouts_reject_related_training_examples(self):
        rows = [
            {'id': 'a', 'condition': 'A', 'family_id': 'same', 'split': 'train'},
            {'id': 'b', 'condition': 'A', 'family_id': 'same', 'split': 'test'},
            {'id': 'c', 'condition': 'A', 'family_id': 'other', 'split': 'validation'},
        ]
        with self.assertRaisesRegex(ValueError, 'families overlap'):
            split_dataset(rows)

    def test_stratified_split_is_repeatable_and_disjoint(self):
        rows = [{'condition': label} for label in ['A', 'B'] for _ in range(20)]
        first, second = split_dataset(rows), split_dataset(rows)
        self.assertEqual([len(part) for part in first], [24, 8, 8])
        for left, right in zip(first, second):
            np.testing.assert_array_equal(left, right)
        self.assertEqual(len(set().union(*map(set, first))), len(rows))

    def test_duplicate_family_does_not_gain_extra_training_weight(self):
        rows = [
            {'id': 'a1', 'condition': 'A', 'family_id': 'a'},
            {'id': 'a2', 'condition': 'A', 'family_id': 'a'},
            {'id': 'b', 'condition': 'A', 'family_id': 'b'},
            {'id': 'c', 'condition': 'B', 'family_id': 'c'},
        ]
        weights = calculate_training_weights(rows, np.arange(4))
        self.assertAlmostEqual(float(weights[0] + weights[1]), float(weights[2]))
        self.assertAlmostEqual(float(weights[:3].sum()), float(weights[3]))
        self.assertAlmostEqual(float(weights.sum()), 4.)

    def test_metrics_keep_label_order_and_unevaluated_classes(self):
        report = evaluate(['B', 'A'], np.array([[.9, .1, 0.], [.8, .2, 0.]]), ['A', 'B', 'C'])
        self.assertEqual(report['accuracy'], .5)
        self.assertEqual(report['confusion_matrix'], [[1, 0, 0], [1, 0, 0], [0, 0, 0]])
        self.assertEqual(report['test_rows'], 2)


if __name__ == '__main__':
    unittest.main()
