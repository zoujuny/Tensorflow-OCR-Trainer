import tfutils as network_utils
from ModelFn import ModelFn

from tensorflow.contrib.learn import ModeKeys
from tensorflow.python.training.training_util import get_global_step
from tensorflow.contrib.learn.python.learn.estimators import model_fn as model_fn_lib


class CNNMDLSTMCTCModelFn(ModelFn):
    def __init__(self, image_width, image_height, num_channels, starting_filter_size, learning_rate, optimizer):
        self.params = {
            "image_width": image_width,
            "image_height": image_height,
            "num_channels": num_channels,
            "starting_filter_size": starting_filter_size,
            "learning_rate": learning_rate,
            "optimizer": optimizer
        }

    @staticmethod
    def model_fn(features, labels, mode, params):
        image_width = params["image_width"]
        image_height = params["image_height"]
        num_channels = params["num_channels"]
        starting_filter_size = params["starting_filter_size"]
        learning_rate = params["learning_rate"]
        optimizer = params["optimizer"]

        input_layer = network_utils.reshape(features["x"], [-1, image_width, image_height, num_channels])
        seq_lens = network_utils.reshape(features["seq_lens"], [-1])
        sparse_labels = network_utils.dense_to_sparse(labels, eos_token=80)

        net = network_utils.conv2d(input_layer, starting_filter_size, 3)
        net = network_utils.max_pool2d(net, 2)
        net = network_utils.mdlstm(net, starting_filter_size * 2)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 3, 3)
        net = network_utils.max_pool2d(net, 2)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.mdlstm(net, starting_filter_size * 4)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 5, 3)
        net = network_utils.max_pool2d(net, 2)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.mdlstm(net, starting_filter_size * 6)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 7, 3)
        net = network_utils.max_pool2d(net, 1)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.mdlstm(net, starting_filter_size * 8)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 9, 3)
        net = network_utils.max_pool2d(net, 1)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.mdlstm(net, starting_filter_size * 10)
        net = network_utils.dropout(net, 0.25)
        net = network_utils.images_to_sequence(net)
        net = network_utils.get_time_major(inputs=net,
                                           num_classes=params["num_classes"],
                                           batch_size=network_utils.get_shape(input_layer)[0],
                                           num_hidden_units=starting_filter_size * 10)
        net = network_utils.transpose(net, (1, 0, 2))

        loss = None
        train_op = None

        if mode != ModeKeys.INFER:
            loss = network_utils.ctc_loss(inputs=net, labels=sparse_labels, sequence_length=seq_lens)

        if mode == ModeKeys.TRAIN:
            optimizer = network_utils.get_optimizer(learning_rate=learning_rate,
                                                    optimizer_name=optimizer)
            train_op = optimizer.minimize(loss=loss, global_step=get_global_step())

        decoded, log_probabilities = network_utils.ctc_beam_search_decoder(inputs=net, sequence_length=seq_lens)
        dense_decoded = network_utils.sparse_to_dense(decoded, name="output")

        predictions = {
            "decoded": dense_decoded,
            "probabilities": log_probabilities
        }

        eval_metric_ops = {
            "label_error_rate": network_utils.label_error_rate(y_pred=decoded, y_true=sparse_labels)
        }

        return model_fn_lib.ModelFnOps(mode=mode,
                                       predictions=predictions,
                                       loss=loss,
                                       train_op=train_op,
                                       eval_metric_ops=eval_metric_ops)
