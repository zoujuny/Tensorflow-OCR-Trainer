import os

from trainer.backend import dataset_utils
from trainer.backend.tf import train
from trainer.backend.tf import evaluate


def train_model(run_params, dataset_dir, checkpoint_dir,
                learning_rate, metrics, loss, optimizer,
                desired_image_size, charset_file, labels_delimiter=' ',
                num_epochs=1, batch_size=1, checkpoint_epochs=1):
    labels_file = os.path.join(dataset_dir, "train.csv")
    images, labels, num_classes = _prepare_dataset(charset_file,
                                                   dataset_dir,
                                                   desired_image_size,
                                                   labels_delimiter,
                                                   labels_file)

    run_params["learning_rate"] = learning_rate
    run_params["optimizer"] = optimizer
    run_params["metrics"] = metrics
    run_params["loss"] = loss

    train(params=run_params,
          features=images,
          labels=labels,
          num_classes=num_classes,
          checkpoint_dir=checkpoint_dir,
          batch_size=batch_size,
          num_epochs=num_epochs,
          save_checkpoint_every_n_epochs=checkpoint_epochs)


def evaluate_model(architecture_params, dataset_dir, charset_file,
                   checkpoint_dir, labels_delimiter=' '):
    labels_file = os.path.join(dataset_dir, "test.csv")
    images, labels, num_classes = _prepare_dataset(charset_file,
                                                   dataset_dir,
                                                   architecture_params['desired_image_size'],
                                                   labels_delimiter,
                                                   labels_file)
    evaluate(architecture_params, images, labels, num_classes, checkpoint_dir)


def _prepare_dataset(charset_file, dataset_dir, desired_image_size, labels_delimiter, labels_file):
    image_paths, labels = dataset_utils.read_dataset_list(
        labels_file, delimiter=labels_delimiter)
    max_label_length = len(max(labels, key=len))
    images = dataset_utils.read_images(data_dir=dataset_dir,
                                       image_paths=image_paths,
                                       image_extension='png')
    images = dataset_utils.resize(images,
                                  desired_height=desired_image_size,
                                  desired_width=desired_image_size)
    images = dataset_utils.binarize(images)
    images = dataset_utils.invert(images)
    classes = dataset_utils.get_characters_from(charset_file)
    images = dataset_utils.images_as_float32(images)
    labels = dataset_utils.encode(labels, classes)
    num_classes = len(classes) + 1
    labels = dataset_utils.pad(labels, max_label_length)
    return images, labels, num_classes
