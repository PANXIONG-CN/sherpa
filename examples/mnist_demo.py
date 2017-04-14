from __future__ import print_function
from __future__ import absolute_import
from hobbit.utils.testing_utils import load_dataset
from hobbit.utils.testing_utils import create_model as my_model


def mnist_demo():
    from hobbit.algorithms import Hyperband
    from hobbit import Hyperparameter

    tmp_folder = './test_repo'

    my_dataset = load_dataset()

    my_hparam_ranges = [Hyperparameter(name='learning_rate', distr_args=(0.0001, 0.1), distribution='log-uniform'),
                        Hyperparameter(name='activation', distr_args=[('sigmoid', 'tanh', 'relu')], distribution='choice'),
                        Hyperparameter(name='dropout', distr_args=(0., 1.), distribution='uniform')]


    hband = Hyperband(model_function=my_model,
                        dataset=my_dataset,
                        hparam_ranges=my_hparam_ranges,
                        repo_dir=tmp_folder)

    tab = hband.run(R=20, eta=3)

    print(tab)

if __name__ == '__main__':
    mnist_demo()