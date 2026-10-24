"""Semantic negative cases for the dense bank's independent public-input audit."""
import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_clocked_effects import audit_dense_words


class DenseReadoutAuditTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        (base / 'healthy').mkdir()
        self.capture = base / 'summary.json'
        rows = [dict(hierarchy=f'DenseStorage.word_{i}', width=i % 64 + 1, depth=1) for i in range(257)]
        rows += [dict(hierarchy=f'DenseStorage.child_{name}.saved', width=64, depth=1) for name in 'abc']
        # Deliberately different from lexical hierarchy order, like StateID order.
        rows.reverse()
        self.binding = dict(state=rows)
        inputs, words = [], []
        total = steps = 0
        for cycle in range(173):
            data = ((1 << 64) - 1 - cycle * 37)
            reset = cycle < 2
            inputs.append(f'DENSE_INPUT cycle={cycle} reset={int(reset)} data={data}')
            total = 0 if reset else (total + data) % (1 << 64)
            steps = 0 if reset else steps + 1
            if cycle + 1 in (2, 39, 132):
                for index, row in enumerate(rows):
                    if '.word_' in row['hierarchy']:
                        i = int(row['hierarchy'].split('word_')[1])
                        value = i + total + steps * (i + 1)
                    else:
                        value = 9 + total
                    value %= 1 << row['width']
                    words.append(f'{cycle + 1} {index} {value:016x}')
        self.log = base / 'healthy/run.log'
        self.words = base / 'healthy/capture.words'
        self.log.write_text('\n'.join(inputs) + '\n')
        self.words.write_text('\n'.join(words) + '\n')

    def test_all_widths_and_repeated_children_from_public_inputs(self):
        self.assertEqual(audit_dense_words(self.capture, self.binding), 780)

    def test_semantic_corruption_and_noncanonical_padding_reject(self):
        text = self.words.read_text()
        for value in ('0000000000000008', '10000000000000009'):
            with self.subTest(value=value):
                self.words.write_text(text.replace('2 0 0000000000000009', '2 0 ' + value, 1))
                with self.assertRaises(FormatError):
                    audit_dense_words(self.capture, self.binding)

    def test_missing_reordered_and_changed_public_inputs_reject(self):
        text = self.log.read_text()
        for changed in (text.replace('cycle=7 ', 'cycle=6 '),
                        text.replace('cycle=7 reset=0 data=18446744073709551356',
                                     'cycle=7 reset=0 data=18446744073709551355'),
                        text.replace('cycle=7 reset=0', 'cycle=7 reset=2')):
            with self.subTest(changed=changed[:40]):
                self.assertNotEqual(changed, text)
                self.log.write_text(changed)
                with self.assertRaises(FormatError):
                    audit_dense_words(self.capture, self.binding)

    def test_missing_duplicate_reshaped_and_unknown_owners_reject(self):
        for kind in ('missing', 'duplicate', 'width', 'depth', 'unknown'):
            rows = copy.deepcopy(self.binding['state'])
            if kind == 'missing':
                rows.pop()
            elif kind == 'duplicate':
                rows[1] = rows[0]
            else:
                rows[0][dict(width='width', depth='depth', unknown='hierarchy')[kind]] = {
                    'width': 63, 'depth': 2, 'unknown': 'DenseStorage.hidden'}[kind]
            with self.subTest(kind=kind), self.assertRaises(FormatError):
                audit_dense_words(self.capture, dict(state=rows))


if __name__ == '__main__':
    unittest.main()
