import tfutils as network_utils

from Model import Model


class CNNMDLSTMCTCModel(Model):
    def __init__(self, input_shape, starting_filter_size, learning_rate, optimizer, num_classes):
        self.params = {
            "input_shape": input_shape,
            "starting_filter_size": starting_filter_size,
            "learning_rate": learning_rate,
            "optimizer": optimizer,
            "num_classes": num_classes
        }

    @staticmethod
    def model_fn(features, labels, mode, params):
        starting_filter_size = params["starting_filter_size"]

        input_layer = network_utils.reshape(features["x"], params["input_shape"])
        seq_lens = network_utils.reshape(features["seq_lens"], [-1])
        sparse_labels = network_utils.dense_to_sparse(labels, eos_token=80)

        net = network_utils.conv2d(input_layer, starting_filter_size, 3)
        net = network_utils.max_pool2d(net, 2)
        seq_lens = network_utils.div(seq_lens, 2)
        net = network_utils.mdlstm(net, starting_filter_size * 2, cell_type="GLSTM")
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 3, 3)
        net = network_utils.max_pool2d(net, 2)
        net = network_utils.dropout(net, 0.25)
        seq_lens = network_utils.div(seq_lens, 2)
        net = network_utils.mdlstm(net, starting_filter_size * 4, cell_type="GLSTM")
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 5, 3)
        net = network_utils.max_pool2d(net, 2)
        net = network_utils.dropout(net, 0.25)
        seq_lens = network_utils.div(seq_lens, 2)
        net = network_utils.mdlstm(net, starting_filter_size * 6, cell_type="GLSTM")
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 7, 3)
        net = network_utils.max_pool2d(net, 1)
        net = network_utils.dropout(net, 0.25)
        seq_lens = network_utils.div(seq_lens, 2, is_floor=False)
        net = network_utils.mdlstm(net, starting_filter_size * 8, cell_type="GLSTM")
        net = network_utils.dropout(net, 0.25)
        net = network_utils.conv2d(net, starting_filter_size * 9, 3)
        net = network_utils.max_pool2d(net, 1)
        net = network_utils.dropout(net, 0.25)
        seq_lens = network_utils.div(seq_lens, 2, is_floor=False)
        net = network_utils.mdlstm(net, starting_filter_size * 10, cell_type="GLSTM")
        net = network_utils.dropout(net, 0.25)
        net = network_utils.collapse_to_rnn_dims(net)
        net = network_utils.get_logits(inputs=net,
                                       num_classes=params["num_classes"],
                                       num_steps=net.shape[1],
                                       num_hidden_units=net.shape[-1])

        loss = None
        train_op = None

        if not network_utils.is_inference(mode):
            loss = network_utils.ctc_loss(labels=sparse_labels, inputs=net, sequence_length=seq_lens)
            network_utils.add_to_summary("loss", loss)

        if network_utils.is_training(mode):
            train_op = network_utils.create_train_op(loss, params["learning_rate"], params["optimizer"])

        decoded, log_probabilities = network_utils.ctc_beam_search_decoder(inputs=net, sequence_length=seq_lens)
        dense_decoded = network_utils.sparse_to_dense(decoded, name="output")
        label_error_rate = network_utils.label_error_rate(y_pred=decoded, y_true=sparse_labels)
        network_utils.add_to_summary("label_error_rate", label_error_rate)

        predictions = {
            "decoded": dense_decoded,
            "probabilities": log_probabilities,
            "label_error_rate": label_error_rate
        }

        return network_utils.create_model_fn(mode=mode,
                                             predictions=predictions,
                                             loss=loss,
                                             train_op=train_op)
