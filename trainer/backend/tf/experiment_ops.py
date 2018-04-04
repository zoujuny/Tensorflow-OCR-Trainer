import numpy as np
import tensorflow as tf

from trainer.backend.GraphKeys import Optimizers
from trainer.backend.GraphKeys import OutputLayers
from trainer.backend.GraphKeys import Metrics
from trainer.backend.GraphKeys import Losses

from trainer.backend.tf import ctc_ops, losses, metric_functions
from trainer.backend.tf.replicate_model_fn import TowerOptimizer
from trainer.backend.tf.util_ops import feed, dense_to_sparse, get_sequence_lengths

from tensorflow.contrib import slim

tf.logging.set_verbosity(tf.logging.INFO)

def _get_loss(loss, labels, inputs, num_classes):
    if loss == Losses.CTC.value:
        inputs = ctc_ops.convert_to_ctc_dims(inputs,
                                             num_classes=num_classes,
                                             num_steps=inputs.shape[1],
                                             num_outputs=inputs.shape[-1])
        labels = dense_to_sparse(labels, token_to_ignore=-1)
        return losses.ctc_loss(labels=labels,
                               inputs=inputs,
                               sequence_length=get_sequence_lengths(inputs))
    raise NotImplementedError(loss + " loss not implemented")


def _sparse_to_dense(sparse_tensor, name="sparse_to_dense"):
    return tf.sparse_to_dense(tf.to_int32(sparse_tensor.indices),
                              tf.to_int32(sparse_tensor.values),
                              tf.to_int32(sparse_tensor.dense_shape),
                              name=name)


def _get_optimizer(learning_rate, optimizer_name):
    if optimizer_name == Optimizers.MOMENTUM.value:
        return tf.train.MomentumOptimizer(learning_rate,
                                          momentum=0.9,
                                          use_nesterov=True)
    if optimizer_name == Optimizers.ADAM.value:
        return tf.train.AdamOptimizer(learning_rate)
    if optimizer_name == Optimizers.ADADELTA.value:
        return tf.train.AdadeltaOptimizer(learning_rate)
    elif optimizer_name == Optimizers.RMSPROP.value:
        return tf.train.RMSPropOptimizer(learning_rate)
    raise NotImplementedError(optimizer_name + " optimizer not supported")


def train(params, features, labels, num_classes, checkpoint_dir,
          batch_size=1, num_epochs=1, save_checkpoint_every_n_epochs=1):
    num_steps_per_epoch = len(features) // batch_size
    save_checkpoint_steps = save_checkpoint_every_n_epochs * num_steps_per_epoch
    params['num_classes'] = num_classes
    params['log_step_count_steps'] = num_steps_per_epoch
    estimator = tf.estimator.Estimator(model_fn=_train_model_fn,
                                       params=params,
                                       model_dir=checkpoint_dir,
                                       config=tf.estimator.RunConfig(
                                           save_checkpoints_steps=save_checkpoint_steps,
                                           log_step_count_steps=num_steps_per_epoch,
                                           save_summary_steps=num_steps_per_epoch
                                       ))
    estimator.train(input_fn=_input_fn(features, labels, batch_size),
                    steps=num_epochs * num_steps_per_epoch)

def evaluate(params, features, labels, num_classes, checkpoint_dir, batch_size):
    params['num_classes'] = num_classes
    estimator = tf.estimator.Estimator(model_fn=_eval_model_fn,
                                       params=params,
                                       model_dir=checkpoint_dir)
    estimator.evaluate(input_fn=_input_fn(features,
                                          labels,
                                          batch_size=batch_size,
                                          num_epochs=1,
                                          shuffle=False))


def _input_fn(features, labels, batch_size=1, num_epochs=None, shuffle=True):
    return tf.estimator.inputs.numpy_input_fn(
        x={"x": np.array(features)},
        y=np.array(labels, dtype=np.int32),
        batch_size=batch_size,
        num_epochs=num_epochs,
        shuffle=shuffle
    )


def _add_to_summary(name, value):
    tf.summary.scalar(name, value)


def _create_train_op(loss, learning_rate, optimizer):
    optimizer = _get_optimizer(learning_rate, optimizer)
    optimizer = TowerOptimizer(optimizer)
    return slim.learning.create_train_op(loss, optimizer, global_step=tf.train.get_or_create_global_step())


def _create_model_fn(mode, predictions, loss=None, train_op=None, eval_metric_ops=None, training_hooks=None):
    return tf.estimator.EstimatorSpec(mode=mode,
                                      predictions=predictions,
                                      loss=loss,
                                      train_op=train_op,
                                      eval_metric_ops=eval_metric_ops,
                                      training_hooks=training_hooks)


def _get_output(inputs, output_layer, num_classes):
    if output_layer == OutputLayers.CTC_DECODER.value:
        inputs = ctc_ops.convert_to_ctc_dims(inputs,
                                             num_classes=num_classes,
                                             num_steps=inputs.shape[1],
                                             num_outputs=inputs.shape[-1])
        decoded, _ = ctc_ops.ctc_beam_search_decoder(inputs)
        return _sparse_to_dense(decoded, name="output")
    raise NotImplementedError(output_layer + " not implemented")


def _get_metrics(metrics, y_pred, y_true, num_classes):
    metrics_dict = {}
    for metric in metrics:
        if metric == Metrics.LABEL_ERROR_RATE.value:
            y_pred = ctc_ops.convert_to_ctc_dims(y_pred,
                                                 num_classes=num_classes,
                                                 num_steps=y_pred.shape[1],
                                                 num_outputs=y_pred.shape[-1])
            y_pred, _ = ctc_ops.ctc_beam_search_decoder(y_pred)
            y_true = dense_to_sparse(y_true, token_to_ignore=-1)
            value = metric_functions.label_error_rate(y_pred,
                                                      y_true,
                                                      metric)
        else:
            raise NotImplementedError(metric + " metric not implemented")
        metrics_dict[metric] = value
    return metrics_dict


def _predict_model_fn(features, mode, params):
    features = _network_fn(features, mode, params)

    outputs = _get_output(features, params["output_layer"], params["num_classes"])
    predictions = {
        "outputs": outputs
    }

    return _create_model_fn(mode, predictions=predictions)

def _eval_model_fn(features, labels, mode, params):
    features = _network_fn(features, mode, params)

    outputs = _get_output(features, params["output_layer"], params["num_classes"])
    predictions = {
        "outputs": outputs
    }

    loss = _get_loss(params["loss"], labels=labels, inputs=features, num_classes=params["num_classes"])
    metrics = _get_metrics(params["metrics"],
                           y_pred=features,
                           y_true=labels,
                           num_classes=params["num_classes"])
    for metric_key in metrics:
        metrics[metric_key] = metric_functions.create_eval_metric(metrics[metric_key])
    return _create_model_fn(mode, predictions=predictions, loss=loss,
                            eval_metric_ops=metrics)

def _train_model_fn(features, labels, mode, params):
    features = _network_fn(features, mode, params)

    outputs = _get_output(features, params["output_layer"],
                          params["num_classes"])
    predictions = {
        "outputs": outputs
    }

    loss = _get_loss(params["loss"], labels=labels,
                     inputs=features, num_classes=params["num_classes"])
    metrics = _get_metrics(params["metrics"],
                           y_pred=features,
                           y_true=labels,
                           num_classes=params["num_classes"])

    train_op = _create_train_op(loss,
                                learning_rate=params["learning_rate"],
                                optimizer=params["optimizer"])

    training_hooks = []
    for metric_key in metrics:
        _add_to_summary(metric_key, metrics[metric_key])
        training_hooks.append(tf.train.LoggingTensorHook(
            {metric_key: metric_key},
            every_n_iter=params["log_step_count_steps"])
        )

    return _create_model_fn(mode,
                            predictions=predictions,
                            loss=loss,
                            train_op=train_op,
                            training_hooks=training_hooks)


def _network_fn(features, mode, params):
    features = features["x"]
    features = _set_dynamic_batch_size(features)
    for layer in params["network"]:
        features = feed(features, layer, is_training=mode == tf.estimator.ModeKeys.TRAIN)
    return features


def _set_dynamic_batch_size(inputs):
    new_shape = [-1]
    new_shape.extend(inputs.get_shape().as_list()[1:])
    inputs = tf.reshape(inputs, new_shape, name="inputs")
    return inputs