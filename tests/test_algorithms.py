"""
SHERPA is a Python library for hyperparameter tuning of machine learning models.
Copyright (C) 2018  Lars Hertel, Peter Sadowski, and Julian Collado.

This file is part of SHERPA.

SHERPA is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SHERPA is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SHERPA.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import absolute_import
import collections
import pandas
import sherpa
import logging
from test_sherpa import get_test_trial


logging.basicConfig(level=logging.DEBUG)
testlogger = logging.getLogger(__name__)


def test_median_stopping_rule():
    results_df = pandas.DataFrame(collections.OrderedDict(
        [('Trial-ID', [1]*3 + [2]*3 + [3]*3),
         ('Status', ['INTERMEDIATE']*9),
         ('Iteration', [1, 2, 3]*3),
         ('a', [1, 1, 1]*3),
         ('b', [2, 2, 2]*3),
         ('Objective', [0.1]*3 + [0.2]*3 + [0.3]*3)]
    ))

    stopper = sherpa.algorithms.MedianStoppingRule(min_iterations=2,
                                                   min_trials=1)

    t = get_test_trial(id=3)

    assert stopper.should_trial_stop(trial=t, results=results_df,
                                     lower_is_better=True)

    stopper = sherpa.algorithms.MedianStoppingRule(min_iterations=4,
                                                   min_trials=1)
    assert not stopper.should_trial_stop(trial=t, results=results_df,
                                         lower_is_better=True)

    stopper = sherpa.algorithms.MedianStoppingRule(min_iterations=2,
                                                   min_trials=4)
    assert not stopper.should_trial_stop(trial=t, results=results_df,
                                         lower_is_better=True)


def test_local_search():
    parameters = [sherpa.Continuous('cont', [0, 1]),
                  sherpa.Ordinal('ord', [1, 2, 3])]

    seed = {'cont': 0.5, 'ord': 2}
    alg = sherpa.algorithms.LocalSearch(seed_configuration=seed)

    study = sherpa.Study(parameters=parameters, algorithm=alg, lower_is_better=True,
                         disable_dashboard=True)

    def mock_objective(p):
        return p['cont']/p['ord']

    # Initial suggestion.
    t = study.get_suggestion()
    tlist = [t]
    tbest = t
    assert t.parameters == seed
    study.add_observation(t, objective=mock_objective(t.parameters),
                          iteration=1)
    study.finalize(t)


    # Perform a suggestion.
    t = study.get_suggestion()
    tlist.append(t)
    if mock_objective(t.parameters) < mock_objective(tbest.parameters):
           tbest = t     
    study.add_observation(t, objective=mock_objective(t.parameters),
                          iteration=1)
    study.finalize(t)
    if t.parameters['ord'] == 2:
        assert t.parameters['cont'] != 0.5
        assert abs(t.parameters['cont'] - 0.5) < 0.2
    else:
        assert t.parameters['cont'] == 0.5
        t.parameters['ord'] in [1,3]
    
    # Do more iterations.
    for i in range(50):
        t = study.get_suggestion()
        #print(t.parameters)
        assert t.parameters['ord'] in [1,2,3]
        assert t.parameters['cont'] >= 0.0 
        assert t.parameters['cont'] <= 1.0 
        # All new suggestions should be based on tbest.
        assert t.parameters['ord'] == tbest.parameters['ord'] \
               or t.parameters['cont'] == tbest.parameters['cont']
        tlist.append(t)
        if mock_objective(t.parameters) < mock_objective(tbest.parameters):
           tbest = t
        study.add_observation(t, objective=mock_objective(t.parameters),
                              iteration=1)
        study.finalize(t)


def test_Iterate_search():
    '''
    The Iterate algorithm should be able to iterate over unhashable types.
    '''
    hp_iter = [{'a': 1, 'b': 'a', 'c': [10]},
               {'a': 1, 'b': 'a', 'c': [10]},
               {'a': 1, 'b': 'b', 'c': [10, 10]},
               {'a': 2, 'b': 'b', 'c': {'key':'value'}},
              ]
    alg = sherpa.algorithms.Iterate(hp_iter)
    parameters = alg.get_parameters()

    assert len(parameters) == 3
    assert set([len(p.range) for p in parameters]) == set([2,2,3])
    
    seen = []
    suggestion = alg.get_suggestion(parameters)
    while suggestion:
        seen.append((suggestion['a'], suggestion['b'], suggestion['c']))
        suggestion = alg.get_suggestion(parameters)

    assert seen == [(1, 'a', [10]), (1, 'a', [10]),
                    (1, 'b', [10,10]), (2, 'b', {'key':'value'})]

def test_grid_search():
    parameters = [sherpa.Choice('a', [1, 2]),
                  sherpa.Choice('b', ['a', 'b']),
                  sherpa.Continuous('c', [1, 4])]

    alg = sherpa.algorithms.GridSearch()

    suggestion = alg.get_suggestion(parameters)
    seen = set()

    while suggestion:
        seen.add((suggestion['a'], suggestion['b'], suggestion['c']))
        suggestion = alg.get_suggestion(parameters)

    assert seen == {(1, 'a', 2), (1, 'a', 3),
                    (1, 'b', 2), (1, 'b', 3),
                    (2, 'a', 2), (2, 'a', 3),
                    (2, 'b', 2), (2, 'b', 3)}


def test_pbt():
    parameters = [sherpa.Continuous(name='param_a', range=[0, 1])]

    algorithm = sherpa.algorithms.PopulationBasedTraining(population_size=20,
                                                          parameter_range={'param_a': [0., 1.2]})

    study = sherpa.Study(parameters=parameters,
                         algorithm=algorithm,
                         lower_is_better=True,
                         disable_dashboard=True)

    for _ in range(20):
        trial = study.get_suggestion()
        print("Trial-ID={}".format(trial.id))
        print(trial.parameters)
        print()
        study.add_observation(trial=trial, iteration=1, objective=trial.id*0.1)
        study.finalize(trial=trial,
                       status='COMPLETED')

    for _ in range(20):
        trial = study.get_suggestion()
        print("Trial-ID={}".format(trial.id))
        print(trial.parameters)
        print()
        parent_param = study.results.loc[study.results['Trial-ID']==int(trial.parameters['load_from'])]['param_a'].iloc[0]
        print(parent_param)
        assert (trial.parameters['param_a'] == 0.8 * parent_param or
                trial.parameters['param_a'] == 1.0 * parent_param or
                trial.parameters['param_a'] == 1.2 * parent_param or
                trial.parameters['param_a'] == 0. or
                trial.parameters['param_a'] == 1.2)
        assert int(trial.parameters['load_from']) <= 10
        study.add_observation(trial=trial, iteration=1, objective=trial.id*0.1)
        study.finalize(trial=trial,
                       status='COMPLETED')

    for _ in range(20):
        trial = study.get_suggestion()
        print("Trial-ID={}".format(trial.id))
        print(trial.parameters)
        print()
        parent_param = study.results.loc[
            study.results['Trial-ID'] == int(trial.parameters['load_from'])][
            'param_a'].iloc[0]
        assert (trial.parameters['param_a'] == 0.8 * parent_param or
                trial.parameters['param_a'] == 1.0 * parent_param or
                trial.parameters['param_a'] == 1.2 * parent_param or
                trial.parameters['param_a'] == 0. or
                trial.parameters['param_a'] == 1.2)
        # assert int(trial.parameters['load_from']) <= 27
        study.add_observation(trial=trial, iteration=1, objective=trial.id*0.1)
        study.finalize(trial=trial,
                       status='COMPLETED')


def test_pbt_ordinal():
    parameters = [sherpa.Ordinal(name='param_a', range=[-1, 0, 1])]

    algorithm = sherpa.algorithms.PopulationBasedTraining(population_size=10)

    study = sherpa.Study(parameters=parameters,
                         algorithm=algorithm,
                         lower_is_better=True,
                         disable_dashboard=True)

    for _ in range(20):
        trial = study.get_suggestion()
        print("Trial-ID={}".format(trial.id))
        print(trial.parameters)
        print()
        study.add_observation(trial=trial, iteration=1, objective=trial.parameters['param_a']*0.1)
        study.finalize(trial=trial,
                       status='COMPLETED')

    for _ in range(20):
        trial = study.get_suggestion()
        print("Trial-ID={}".format(trial.id))
        print(trial.parameters)
        print()
        assert trial.parameters['param_a'] in (-1, 0, 1)
        study.add_observation(trial=trial, iteration=1, objective=trial.parameters['param_a']*0.1)
        study.finalize(trial=trial,
                       status='COMPLETED')
