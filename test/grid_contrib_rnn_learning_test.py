import unittest

import tensorflow as tf
from tensorflow.contrib import grid_rnn
from tensorflow.contrib import rnn


class GridRNNTest(tf.test.TestCase):
    def setUp(self):
        self.num_features = 1
        self.time_steps = 1
        self.batch_size = 1
        tf.reset_default_graph()
        self.input_layer = tf.placeholder(tf.float32, [self.batch_size, self.time_steps, self.num_features])
        self.cell = grid_rnn.Grid1LSTMCell(num_units=1)

    def test_simple_grid_rnn(self):
        self.input_layer = tf.unstack(self.input_layer, self.time_steps, 1)
        rnn.static_rnn(self.cell, self.input_layer, dtype=tf.float32)


class BidirectionalGridRNNTest(tf.test.TestCase):
    def setUp(self):
        self.num_features = 1
        self.time_steps = 1
        self.batch_size = 1
        tf.reset_default_graph()
        self.input_layer = tf.placeholder(tf.float32, [self.batch_size, self.time_steps, self.num_features])
        self.cell_fw = grid_rnn.Grid1LSTMCell(num_units=8)
        self.cell_bw = grid_rnn.Grid1LSTMCell(num_units=8)

    def test_simple_bidirectional_grid_rnn(self):
        self.input_layer = tf.unstack(self.input_layer, self.time_steps, 1)
        rnn.static_bidirectional_rnn(self.cell_fw, self.cell_bw, self.input_layer, dtype=tf.float32)


class StackBidirectionalGridRNNTest(tf.test.TestCase):
    def setUp(self):
        self.num_features = 1
        self.time_steps = 1
        self.batch_size = 1
        tf.reset_default_graph()
        self.input_layer = tf.placeholder(tf.float32, [self.batch_size, self.time_steps, self.num_features])
        self.cells_fw = rnn.MultiRNNCell([grid_rnn.Grid1LSTMCell(num_units=8) for _ in range(2)])
        self.cells_bw = rnn.MultiRNNCell([grid_rnn.Grid1LSTMCell(num_units=8) for _ in range(2)])

    @unittest.skip("Doesn't work...")
    def test_stack_bidirectional_grid_rnn(self):
        self.input_layer = tf.unstack(self.input_layer, self.time_steps, 1)
        tf.nn.bidirectional_dynamic_rnn(self.cells_fw, self.cells_bw, self.input_layer, dtype=tf.float32)


if __name__ == '__main__':
    tf.test.main()