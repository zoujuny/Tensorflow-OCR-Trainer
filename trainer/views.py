from flask import request, render_template, flash, redirect, url_for, send_from_directory

from trainer import app
from trainer.backend import GraphKeys
from trainer.controllers import package_model_files
from trainer.controllers import delete_file
from trainer.controllers import delete_folder
from trainer.controllers import get_architecture_path
from trainer.controllers import get_architecture_file_contents
from trainer.controllers import get_dataset
from trainer.controllers import get_dataset_list_with_amount_of_training_and_testing_data
from trainer.controllers import get_directory_list_from_config
from trainer.controllers import get_enum_values
from trainer.controllers import get_model_path
from trainer.controllers import get_running_tasks
from trainer.controllers import get_log
from trainer.controllers import request_connection
from trainer.controllers import run_learning_task
from trainer.controllers import save_model_as_json
from trainer.controllers import stop_running
from trainer.controllers import upload_dataset
from trainer.controllers import visualize_model


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/architectures', methods=['GET', 'POST'])
def architectures():
    if request.method == 'POST':
        saving_message = save_model_as_json()
        flash(saving_message)
    network_architectures = _get_network_architectures()
    return render_template("architectures.html",
                           network_architectures=network_architectures)


@app.route('/view_architecture/<architecture_name>')
def view_architecture(architecture_name):
    architecture = get_architecture_file_contents(architecture_name)
    return render_template("view_architecture.html",
                           architecture=architecture,
                           architecture_name=architecture_name)


def _get_network_architectures():
    network_architectures = get_directory_list_from_config('ARCHITECTURES_DIRECTORY')
    network_architectures = _get_names(network_architectures)
    return network_architectures


def _get_names(network_architectures):
    return [network_architecture.split('.')[0]
            for network_architecture in network_architectures]


@app.route('/create_network_architecture')
def create_network_architecture():
    return render_template("create_network_architecture.html",
                           layer_types=get_enum_values(GraphKeys.LayerTypes),
                           padding_types=get_enum_values(GraphKeys.PaddingTypes),
                           cell_types=get_enum_values(GraphKeys.CellTypes),
                           activation_functions=get_enum_values(GraphKeys.ActivationFunctions),
                           output_layers=get_enum_values(GraphKeys.OutputLayers))


@app.route('/delete/<architecture_name>', methods=['POST'])
def delete_architecture(architecture_name):
    delete_file(get_architecture_path(architecture_name))
    flash(architecture_name + " has been deleted.")
    return redirect(url_for('architectures'))


@app.route('/dataset_form')
def dataset_form():
    return render_template("dataset_form.html")


@app.route('/dataset', methods=['GET', 'POST'])
def dataset():
    if request.method == 'POST':
        if 'dataset_zip' not in request.files:
            flash('No labels file part.')
            return redirect(request.url)
        dataset_zip = request.files['dataset_zip']
        if not dataset_zip:
            flash('No dataset zip file selected')
            return redirect(request.url)
        upload_message = upload_dataset(dataset_zip)
        flash(upload_message)
    return render_template("dataset.html", dataset_list=_get_dataset_list_and_details())


def _get_dataset_list_and_details():
    return get_dataset_list_with_amount_of_training_and_testing_data()

@app.route('/delete_dataset/<dataset_name>', methods=['POST'])
def delete_dataset(dataset_name):
    delete_folder(get_dataset(dataset_name))
    flash(dataset_name + " has been deleted.")
    return redirect(url_for('dataset'))


def _get_dataset_list():
    dataset_list = get_directory_list_from_config('DATASET_DIRECTORY')
    return dataset_list


@app.route('/train')
def train():
    return render_template("train.html",
                           dataset_list=_get_dataset_list(),
                           network_architectures=_get_network_architectures(),
                           losses=get_enum_values(GraphKeys.Losses),
                           optimizers=get_enum_values(GraphKeys.Optimizers),
                           metrics=get_enum_values(GraphKeys.Metrics))


@app.route('/retrain/<model_name>')
def retrain(model_name):
    return render_template("retrain.html", model_name=model_name,
                           optimizers=get_enum_values(GraphKeys.Optimizers))


@app.route('/tasks/<task>', methods=['GET', 'POST'])
def tasks(task):
    if request.method == 'POST':
        run_learning_task(task)
        flash(task + " has started.")
    running_tasks = get_running_tasks()
    return render_template('tasks.html', running_tasks=running_tasks)


@app.route('/terminate/<task>', methods=['POST'])
def terminate(task):
    message = stop_running(task)
    flash(message)
    return redirect(url_for('tasks', task='view'))


@app.route('/models')
def models():
    return render_template("models.html",
                           models=get_directory_list_from_config('MODELS_DIRECTORY'),
                           dataset_list=_get_dataset_list())


@app.route('/visualize/<model_name>')
def visualize(model_name):
    visualize_model(model_name, app.config['VISUALIZATION_HOST'])
    request_connection("http://localhost:6006")
    return redirect("http://localhost:6006")

@app.route('/view_logs/<model_name>')
def view_logs(model_name):
    train_log = get_log(model_name, "train")
    test_log = get_log(model_name, "test")
    return render_template("view_logs.html",
                           train_log=train_log,
                           test_log=test_log)


@app.route('/delete_model/<model_name>', methods=['POST'])
def delete_model(model_name):
    delete_folder(get_model_path(model_name))
    flash(model_name + " has been deleted.")
    return redirect(url_for('models'))


@app.route('/{}/<model_name>/{}'.format(app.config['MODELS_DIRECTORY'], app.config['MODEL_ZIP_FILENAME']))
def export_model(model_name):
    model_abs_path = package_model_files(model_name)
    return send_from_directory(model_abs_path, app.config['MODEL_ZIP_FILENAME'])


@app.errorhandler(404)
def url_error(e):
    print(e)
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    print(e)
    return render_template("500.html"), 500
