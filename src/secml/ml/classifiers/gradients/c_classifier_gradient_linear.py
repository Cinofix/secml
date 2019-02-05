"""
.. module:: CClassifierGradientLinear
   :synopsis: Common interface for the implementations of linear classifier
              gradients

.. moduleauthor:: Ambra Demontis <ambra.demontis@diee.unica.it>

"""
from abc import abstractmethod

from secml.array import CArray
from secml.ml.classifiers.gradients import CClassifierGradient
from secml.ml.classifiers.clf_utils import convert_binary_labels


class CClassifierGradientLinear(CClassifierGradient):
    __class_type = 'linear'

    @abstractmethod
    def _C(self, clf):
        raise NotImplementedError()

    def fd_w(self, x):
        """
        Derivative of the discriminant function w.r.t. the classifier
        weights
        """
        d = x.T  # where x is normalized if the classifier has a
        # normalizer
        return d

    def fd_b(self, x):
        """
        Derivative of the discriminant function w.r.t. the classifier
        bias
        """
        x = x.atleast_2d()  # where x is normalized if the classifier has a
        # normalizer
        k = x.shape[0]  # number of samples
        d = CArray.ones((1, k))
        return d

    def fd_params(self, clf, x):
        """
        Derivative of the discriminant function w.r.t. the classifier
        parameters
        """
        if clf.preprocess is not None:
            x = clf.preprocess.normalize(x)

        fd_w = self.fd_w(x)
        fd_b = self.fd_b(x)
        d = fd_w.append(fd_b, axis=0)
        return d

    def fd_x(self, clf, x=None, y=1):
        """
        Derivative of the discriminant function w.r.t. an input sample
        """
        # Gradient sign depends on input label (0/1)
        return convert_binary_labels(y) * clf.w

    def dreg_s(self, clf):
        """
        Derivative of the regularizer w.r.t. the score
        """
        return self._reg.dregularizer(clf.w)

    def L_d_params(self, clf, x, y, loss=None, regularized=True):
        """
        Derivative of the classifier classifier loss function (regularizer
        included) w.r.t. the classifier parameters

        If the loss is equal to None (default) the classifier loss is used
        to compute the derivative.

        dL / d_params = dL / df * df / d_params + dReg / d_params

        Parameters
        ----------
        x : CArray
            features of the dataset on which the loss is computed
        y :  CArray
            features of the training samples
        loss: None (default) or CLoss
            If the loss is equal to None (default) the classifier loss is used
            to compute the derivative.
        regularized: boolean
            If True (default) the loss on which the derivative is computed
            is the loss on the given samples + the regularizer,
            which is not considered if the argument is False
        """

        if loss is None:
            loss = self._loss

        y = y.ravel()

        w = CArray(clf.w.ravel()).T  # column vector
        C = self._C(clf)

        x = x.atleast_2d()

        s = clf.decision_function(x)

        if clf.preprocess is not None:
            x = clf.preprocess.normalize(x)

        fd_w = self.fd_w(x)  # d * n_samples
        fd_b = self.fd_b(x)  # 1 * n_samples

        grad_w = C * (loss.dloss(y, score=s).atleast_2d() * fd_w)
        grad_b = C * (loss.dloss(y, score=s).atleast_2d() * fd_b)

        if regularized:
            grad_w += self._reg.dregularizer(w)

        grad = grad_w.append(grad_b, axis=0)

        return grad  # (d +1) * n_samples

    def _L_tot(self, x, y, clf):
        """
        Classifier total loss
        L_tot = loss computed on the training samples + regularizer
        """
        y = y.ravel()

        w = CArray(clf.w.ravel()).T  # column vector
        C = clf.C

        x = x.atleast_2d()

        s = clf.decision_function(x)

        loss = C * self._loss.loss(y, score=s) + self._reg.regularizer(w)

        return loss

    def _params(self, clf):
        """
        Classifier parameters
        """
        return clf.w.append(CArray(clf.b), axis=None)

    def _change_params(self, params, clf):
        new_clf = clf.deepcopy()
        new_clf._w = params[:-1]
        new_clf._b = params[-1]
        return new_clf