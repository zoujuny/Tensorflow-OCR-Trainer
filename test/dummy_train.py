from architecture_enum import Architectures
from optimizer_enum import Optimizers
from train_using_tf_estimator import train

def main():
    train(labels_file='dummy_labels_file.txt',
          data_dir='dummy_data/',
          labels_delimiter=' ',
          desired_image_height=64,
          desired_image_width=3200,
          architecture=Architectures.CNNMDLSTM,
          num_hidden_units=16,
          optimizer=Optimizers.MOMENTUM,
          learning_rate=0.001,
          test_fraction=0.3,
          num_epochs=1,
          validation_steps=1,
          batch_size=1)


if __name__ == '__main__':
    main()