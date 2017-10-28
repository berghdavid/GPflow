# Copyright 2016 the GPflow authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.from __future__ import print_function

from __future__ import print_function

import unittest
import tensorflow as tf

import numpy as np
from numpy.testing import assert_almost_equal

import gpflow
from gpflow import test_util


class TestOptimize(test_util.GPflowTestCase):
    def setUp(self):
        rng = np.random.RandomState(0)

        class Quadratic(gpflow.models.Model):
            def __init__(self):
                gpflow.models.Model.__init__(self)
                self.x = gpflow.Param(rng.randn(10))

            @gpflow.params_as_tensors
            def _build_likelihood(self):
                return tf.negative(tf.reduce_sum(tf.square(self.x)))

        self.m = Quadratic()

    def test_adam(self):
        with self.test_context():
            m = self.m
            opt = gpflow.train.AdamOptimizer(0.01)
            m.compile()
            opt.minimize(m, maxiter=5000)
            self.assertTrue(m.x.read_value().max() < 1e-2)

    def test_lbfgsb(self):
        with self.test_context():
            m = self.m
            m.compile()
            opt = gpflow.train.ScipyOptimizer(options={'disp': False, 'maxiter': 1000})
            opt.minimize(m)
            self.assertTrue(m.x.read_value().max() < 1e-6)


class EmptyTest(test_util.GPflowTestCase):
    class Empty(gpflow.models.Model):
        def _build_likelihood(self):
            return tf.convert_to_tensor(1., dtype=gpflow.settings.tf_float)

    def test_compile_model_without_parameters(self):
        with self.test_context():
            m = EmptyTest.Empty()
            m.compile()
            assert_almost_equal(m.compute_log_likelihood(), 1.0)
            assert_almost_equal(m.compute_log_prior(), 0.0)

    def test_parameters_list_empty(self):
        with self.test_context():
            m = EmptyTest.Empty()
            self.assertEqual(list(m.parameters), [])
            self.assertEqual(list(m.trainable_parameters), [])
            self.assertEqual(list(m.params), [])
            m.compile()
            self.assertEqual(list(m.parameters), [])
            self.assertEqual(list(m.trainable_parameters), [])
            self.assertEqual(list(m.params), [])

    def test_objective_tensor(self):
        with self.test_context():
            m = EmptyTest.Empty()
            self.assertEqual(m.objective, None)
            m.compile()
            self.assertTrue(gpflow.misc.is_tensor(m.objective))


class NotImplementedModelTest(test_util.GPflowTestCase):
    def no_likelihood_model_test(self):
        class NoLikelihoodModel(gpflow.models.Model):
            pass

        with self.assertRaises(NotImplementedError):
            m = NoLikelihoodModel()
            m.compile()

class ReplaceParameterTest(test_util.GPflowTestCase):

    class Origin(gpflow.models.Model):
        def __init__(self):
            super(ReplaceParameterTest.Origin, self).__init__()
            self.a = gpflow.Param(1.)
            self.b = gpflow.Param(2.)

        @gpflow.params_as_tensors
        def _build_likelihood(self):
            return tf.square(self.a) + tf.square(self.b)

    def test_replace_parameter(self):
        class OriginSuccess(ReplaceParameterTest.Origin):
            def __init__(self):
                super(OriginSuccess, self).__init__()
                self.b = gpflow.Param(np.array(3.))

        class OriginAllDataholders(ReplaceParameterTest.Origin):
            def __init__(self):
                super(OriginAllDataholders, self).__init__()
                self.a = gpflow.DataHolder(np.array(2.))
                self.b = gpflow.DataHolder(np.array(2.))

        with self.test_context():
            m0 = self.Origin()
            m0.compile()
            assert_almost_equal(m0.compute_log_likelihood(), 5.0)

            m1 = OriginSuccess()
            m1.compile()
            assert_almost_equal(m1.compute_log_likelihood(), 10.0)

            m2 = OriginAllDataholders()
            m2.compile()
            assert_almost_equal(m2.compute_log_likelihood(), 8.0)


class KeyboardRaiser:
    """
    This wraps a function and makes it raise a KeyboardInterrupt after some number of calls
    """

    def __init__(self, iters_to_raise):
        self.iters_to_raise = iters_to_raise
        self.count = 0

    def __call__(self, *a, **kw):
        self.count += 1
        if self.count >= self.iters_to_raise:
            raise KeyboardInterrupt


class TestKeyboardCatching(test_util.GPflowTestCase):
    def setUp(self):
        X = np.random.randn(1000, 3)
        Y = np.random.randn(1000, 3)
        Z = np.random.randn(100, 3)
        self.m = gpflow.models.SGPR(X, Y, Z=Z, kern=gpflow.kernels.RBF(3))

    def test_optimize_np(self):
        with self.test_context():
            m = self.m
            m.compile()
            x_before = m.read_trainables()
            options = {'maxiter': 1000, 'gtol': 0, 'ftol': 0}
            opt = gpflow.train.ScipyOptimizer(options=options)
            step = 15
            raiser = KeyboardRaiser(step)
            opt.minimize(m, step_callback=raiser)
            self.assertEqual(raiser.count, step)
            x_after = m.read_trainables()
            before = np.hstack([np.hstack(np.hstack([x])) for x in x_before])
            after = np.hstack([np.hstack(np.hstack([x])) for x in x_after])
            self.assertFalse(np.allclose(before, after))

    # TODO(@awav)
    #def test_optimize_tf(self):
    #    with self.test_context():
    #        x0 = self.m.get_free_state()
    #        callback = KeyboardRaiser(5, lambda x: None)
    #        o = tf.train.AdamOptimizer()
    #        self.m.optimize(o, maxiter=10, callback=callback)
    #        x1 = self.m.get_free_state()
    #        self.assertFalse(np.allclose(x0, x1))


class TestLikelihoodAutoflow(test_util.GPflowTestCase):
    def setUp(self):
        X = np.random.randn(1000, 3)
        Y = np.random.randn(1000, 3)
        Z = np.random.randn(100, 3)
        self.m = gpflow.models.SGPR(X, Y, Z=Z, kern=gpflow.kernels.RBF(3))

    def test_lik_and_prior(self):
        m = self.m
        with self.test_context():
            m.compile()
            l0 = m.compute_log_likelihood()
            p0 = m.compute_log_prior()
            m.clear()

        with self.test_context():
            m.kern.variance.prior = gpflow.priors.Gamma(1.4, 1.6)
            m.compile()
            l1 = m.compute_log_likelihood()
            p1 = m.compute_log_prior()
            m.clear()

        self.assertEqual(p0, 0.0)
        self.assertNotEqual(p0, p1)
        self.assertEqual(l0, l1)


class TestName(test_util.GPflowTestCase):
    def test_name(self):
        m1 = gpflow.models.Model()
        self.assertEqual(m1.name, 'Model')
        m2 = gpflow.models.Model(name='foo')
        self.assertEqual(m2.name, 'foo')


# class TestNoRecompileThroughNewModelInstance(test_util.GPflowTestCase):
#     """ Regression tests for Bug #454 """

#     def setUp(self):
#         self.X = np.random.rand(10, 2)
#         self.Y = np.random.rand(10, 1)

#     def test_gpr(self):
#         with self.test_context():
#             m1 = gpflow.models.GPR(self.X, self.Y, gpflow.kernels.Matern32(2))
#             m1.compile()
#             m2 = gpflow.models.GPR(self.X, self.Y, gpflow.kernels.Matern32(2))
#             self.assertFalse(m1._needs_recompile)

#     def test_sgpr(self):
#         with self.test_context():
#             m1 = gpflow.models.SGPR(self.X, self.Y, gpflow.kernels.Matern32(2), Z=self.X)
#             m1.compile()
#             m2 = gpflow.models.SGPR(self.X, self.Y, gpflow.kernels.Matern32(2), Z=self.X)
#             self.assertFalse(m1._needs_recompile)

#     def test_gpmc(self):
#         with self.test_context():
#             m1 = gpflow.models.GPMC(
#                 self.X, self.Y,
#                 gpflow.kernels.Matern32(2),
#                 likelihood=gpflow.likelihoods.StudentT())
#             m1.compile()
#             m2 = gpflow.models.GPMC(
#                     self.X, self.Y,
#                     gpflow.kernels.Matern32(2),
#                     likelihood=gpflow.likelihoods.StudentT())
#             self.assertFalse(m1._needs_recompile)

#     def test_sgpmc(self):
#         with self.test_context():
#             m1 = gpflow.models.SGPMC(
#                 self.X, self.Y,
#                 gpflow.kernels.Matern32(2),
#                 likelihood=gpflow.likelihoods.StudentT(),
#                 Z=self.X)
#             m1.compile()
#             m2 = gpflow.models.SGPMC(
#                 self.X, self.Y,
#                 gpflow.kernels.Matern32(2),
#                 likelihood=gpflow.likelihoods.StudentT(),
#                 Z=self.X)
#             self.assertFalse(m1._needs_recompile)

#     def test_svgp(self):
#         with self.test_context():
#             m1 = gpflow.models.SVGP(
#                 self.X, self.Y,
#                 gpflow.kernels.Matern32(2),
#                 likelihood=gpflow.likelihoods.StudentT(),
#                 Z=self.X)
#             m1.compile()
#             m2 = gpflow.models.SVGP(
#                 self.X, self.Y,
#                 gpflow.kernels.Matern32(2),
#                 likelihood=gpflow.likelihoods.StudentT(),
#                 Z=self.X)
#             self.assertFalse(m1._needs_recompile)

#     def test_vgp(self):
#         with self.test_context():
#             m1 = gpflow.models.VGP(
#                 self.X, self.Y,
#                 gpflow.kernels.Matern32(2),
#                 likelihood=gpflow.likelihoods.StudentT())
#             m1.compile()
#             m2 = gpflow.models.VGP(
#                 self.X, self.Y,
#                 gpflow.kernels.Matern32(2),
#                 likelihood=gpflow.likelihoods.StudentT())
#             self.assertFalse(m1._needs_recompile)


if __name__ == "__main__":
    unittest.main()
