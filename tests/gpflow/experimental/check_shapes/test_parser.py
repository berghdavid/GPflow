# Copyright 2022 The GPflow Contributors. All Rights Reserved.
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
# limitations under the License.

# pylint: disable=unused-argument  # Bunch of fake functions below has unused arguments.

from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from gpflow.experimental.check_shapes import check_shapes
from gpflow.experimental.check_shapes.config import set_rewrite_docstrings
from gpflow.experimental.check_shapes.exceptions import SpecificationParseError
from gpflow.experimental.check_shapes.parser import parse_and_rewrite_docstring, parse_function_spec
from gpflow.experimental.check_shapes.specs import ParsedFunctionSpec, ParsedNoteSpec

from .utils import (
    TestContext,
    current_line,
    make_arg_spec,
    make_argument_ref,
    make_shape_spec,
    varrank,
)


@dataclass
class TestData:
    test_id: str
    function_spec_strs: Tuple[str, ...]
    expected_function_spec: ParsedFunctionSpec
    doc: Optional[str]
    expected_doc: Optional[str]

    def __str__(self) -> str:
        return self.test_id


_TEST_DATA = [
    TestData(
        "constant_dimensions",
        (
            "a: [2, 3]",
            "b: [2, 4]",
            "return: [3, 4]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec(2, 3),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec(2, 4),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec(3, 4),
                    note=None,
                ),
            ),
            (),
        ),
        """
        :param a: Parameter a.
        :param b: Parameter b.
        :returns: Return value.
        """,
        """
        :param a:
            * **a** has shape [2, 3].

            Parameter a.
        :param b:
            * **b** has shape [2, 4].

            Parameter b.
        :returns:
            * **return** has shape [3, 4].

            Return value.
        """,
    ),
    TestData(
        "variable_dimensions",
        (
            "a: [d1, d2]",
            "b: [d1, d3]",
            "return: [d2, d3]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec("d1", "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec("d1", "d3"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec("d2", "d3"),
                    note=None,
                ),
            ),
            (),
        ),
        """
        :param a: Parameter a.
        :param b: Parameter b.
        :returns: Return value.
        """,
        """
        :param a:
            * **a** has shape [*d1*, *d2*].

            Parameter a.
        :param b:
            * **b** has shape [*d1*, *d3*].

            Parameter b.
        :returns:
            * **return** has shape [*d2*, *d3*].

            Return value.
        """,
    ),
    TestData(
        "variable_rank",
        (
            "a: [*ds]",
            "b: [ds..., d1]",
            "c: [d1, ds..., d2]",
            "d: [d1, ds...]",
            "return: [*ds, d1, d2]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec(varrank("ds")),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec(varrank("ds"), "d1"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("c"),
                    make_shape_spec("d1", varrank("ds"), "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("d"),
                    make_shape_spec("d1", varrank("ds")),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec(varrank("ds"), "d1", "d2"),
                    note=None,
                ),
            ),
            (),
        ),
        """
        :param a: Parameter a.
        :param b: Parameter b.
        :param c: Parameter c.
        :param d: Parameter d.
        :returns: Return value.
        """,
        """
        :param a:
            * **a** has shape [*ds*...].

            Parameter a.
        :param b:
            * **b** has shape [*ds*..., *d1*].

            Parameter b.
        :param c:
            * **c** has shape [*d1*, *ds*..., *d2*].

            Parameter c.
        :param d:
            * **d** has shape [*d1*, *ds*...].

            Parameter d.
        :returns:
            * **return** has shape [*ds*..., *d1*, *d2*].

            Return value.
        """,
    ),
    TestData(
        "anonymous",
        (
            "a: [., d1]",
            "b: [None, d2]",
            "c: [..., d1]",
            "d: [*, d2]",
            "return: [..., d1, d2]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec(None, "d1"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec(None, "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("c"),
                    make_shape_spec(varrank(None), "d1"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("d"),
                    make_shape_spec(varrank(None), "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec(varrank(None), "d1", "d2"),
                    note=None,
                ),
            ),
            (),
        ),
        """
        :param a: Parameter a.
        :param b: Parameter b.
        :param c: Parameter c.
        :param d: Parameter d.
        :returns: Return value.
        """,
        """
        :param a:
            * **a** has shape [., *d1*].

            Parameter a.
        :param b:
            * **b** has shape [., *d2*].

            Parameter b.
        :param c:
            * **c** has shape [..., *d1*].

            Parameter c.
        :param d:
            * **d** has shape [..., *d2*].

            Parameter d.
        :returns:
            * **return** has shape [..., *d1*, *d2*].

            Return value.
        """,
    ),
    TestData(
        "scalars",
        (
            "a: []",
            "b: []",
            "return: []",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec(),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec(),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec(),
                    note=None,
                ),
            ),
            (),
        ),
        """
        :param a: Parameter a.
        :param b: Parameter b.
        :returns: Return value.
        """,
        """
        :param a:
            * **a** has shape [].

            Parameter a.
        :param b:
            * **b** has shape [].

            Parameter b.
        :returns:
            * **return** has shape [].

            Return value.
        """,
    ),
    TestData(
        "argument_refs",
        (
            "x.ins[0]: [a_batch..., 1]",
            "x.ins[1]: [b_batch..., 2]",
            "return[0].out: [a_batch..., 3]",
            "return[1].out: [b_batch..., 4]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("x", "ins", 0),
                    make_shape_spec(varrank("a_batch"), 1),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("x", "ins", 1),
                    make_shape_spec(varrank("b_batch"), 2),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 0, "out"),
                    make_shape_spec(varrank("a_batch"), 3),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 1, "out"),
                    make_shape_spec(varrank("b_batch"), 4),
                    note=None,
                ),
            ),
            (),
        ),
        """
        :param x: Parameter x.
        :returns: Return value.
        """,
        """
        :param x:
            * **x.ins[0]** has shape [*a_batch*..., 1].
            * **x.ins[1]** has shape [*b_batch*..., 2].

            Parameter x.
        :returns:
            * **return[0].out** has shape [*a_batch*..., 3].
            * **return[1].out** has shape [*b_batch*..., 4].

            Return value.
        """,
    ),
    TestData(
        "notes",
        (
            "a: [d1, d2]",
            "# Some generic note.",
            "b: [d1, d3]  #   Some note \n on B. \n  ",
            "return: [d2, d3]#Some note on the result.",
            "# Some other\ngeneric note.",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec("d1", "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec("d1", "d3"),
                    note=ParsedNoteSpec("Some note on B."),
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec("d2", "d3"),
                    note=ParsedNoteSpec("Some note on the result."),
                ),
            ),
            (
                ParsedNoteSpec("Some generic note."),
                ParsedNoteSpec("Some other generic note."),
            ),
        ),
        """
        Some doctring.

        :param a: Parameter a.
        :param b: Parameter b.
        :returns: Return value.
        """,
        """
        Some doctring.

        Some generic note.

        Some other generic note.

        :param a:
            * **a** has shape [*d1*, *d2*].

            Parameter a.
        :param b:
            * **b** has shape [*d1*, *d3*]. Some note on B.

            Parameter b.
        :returns:
            * **return** has shape [*d2*, *d3*]. Some note on the result.

            Return value.
        """,
    ),
    TestData(
        "no_docstring",
        (
            "a: [d1, d2]",
            "b: [d1, d3]",
            "return: [d2, d3]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec("d1", "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec("d1", "d3"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec("d2", "d3"),
                    note=None,
                ),
            ),
            (),
        ),
        None,
        None,
    ),
    TestData(
        "partial_docstring",
        (
            "a: [d1, d2]",
            "b: [d1, d3]",
            "return: [d2, d3]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec("d1", "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec("d1", "d3"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec("d2", "d3"),
                    note=None,
                ),
            ),
            (),
        ),
        """
        :param b: Parameter b.
        """,
        """
        :param b:
            * **b** has shape [*d1*, *d3*].

            Parameter b.
        """,
    ),
    TestData(
        "no_indent",
        (
            "a: [d1, d2]",
            "b: [d1, d3]",
            "return: [d2, d3]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec("d1", "d2"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("b"),
                    make_shape_spec("d1", "d3"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec("d2", "d3"),
                    note=None,
                ),
            ),
            (),
        ),
        """:param b: Parameter b.""",
        """:param b:
    * **b** has shape [*d1*, *d3*].

    Parameter b.""",
    ),
    TestData(
        "other_info_fields",
        (
            "a: [batch..., n_features]",
            "return: [batch..., 1]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec(varrank("batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec(varrank("batch"), 1),
                    note=None,
                ),
            ),
            (),
        ),
        """
        This is a boring docstring.

        :meta: Blah blah.
        :param a: Some stuff about argument `a`.
        :type a: TensorType
        :meta: More chaff.
        :returns: Some description of the return type.
        :rtype: TensorType
        """,
        """
        This is a boring docstring.

        :meta: Blah blah.
        :param a:
            * **a** has shape [*batch*..., *n_features*].

            Some stuff about argument `a`.
        :type a: TensorType
        :meta: More chaff.
        :returns:
            * **return** has shape [*batch*..., 1].

            Some description of the return type.
        :rtype: TensorType
        """,
    ),
    TestData(
        "other_colons",
        (
            "a: [batch..., n_features]",
            "return: [batch..., 1]",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("a"),
                    make_shape_spec(varrank("batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return"),
                    make_shape_spec(varrank("batch"), 1),
                    note=None,
                ),
            ),
            (),
        ),
        """
        This: is a docstring, :: with some extra :s in it.

        Here: are: some more:.

        :param a: Some stuff about: argument `a`.
        :returns: Some description of the:: return type.
        """,
        """
        This: is a docstring, :: with some extra :s in it.

        Here: are: some more:.

        :param a:
            * **a** has shape [*batch*..., *n_features*].

            Some stuff about: argument `a`.
        :returns:
            * **return** has shape [*batch*..., 1].

            Some description of the:: return type.
        """,
    ),
    TestData(
        "funny_formatting_1",
        (
            "train.features: [train_batch..., n_features]",
            "train.labels: [train_batch..., n_labels]  # Label note.",
            "test_features: [test_batch..., n_features]",
            "return[0]: [test_batch..., n_labels]",
            "return[1]: [test_batch..., n_labels]",
            "# Function note.",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("train", "features"),
                    make_shape_spec(varrank("train_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("train", "labels"),
                    make_shape_spec(varrank("train_batch"), "n_labels"),
                    note=ParsedNoteSpec("Label note."),
                ),
                make_arg_spec(
                    make_argument_ref("test_features"),
                    make_shape_spec(varrank("test_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 0),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 1),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
            ),
            (ParsedNoteSpec("Function note."),),
        ),
        """
        Predict mean and variance from some test features.

        First trains a model an `train`, then makes a prediction from the model and `test`.

        :param train:
            Data to train on.

        :param test_features:
            Features to make test prediction from.

        :returns:
            Model mean and variance prediction.
        """,
        """
        Predict mean and variance from some test features.

        First trains a model an `train`, then makes a prediction from the model and `test`.

        Function note.

        :param train:
            * **train.features** has shape [*train_batch*..., *n_features*].
            * **train.labels** has shape [*train_batch*..., *n_labels*]. Label note.

            Data to train on.

        :param test_features:
            * **test_features** has shape [*test_batch*..., *n_features*].

            Features to make test prediction from.

        :returns:
            * **return[0]** has shape [*test_batch*..., *n_labels*].
            * **return[1]** has shape [*test_batch*..., *n_labels*].

            Model mean and variance prediction.
        """,
    ),
    TestData(
        "funny_formatting_2",
        (
            "train.features: [train_batch..., n_features]",
            "train.labels: [train_batch..., n_labels]  # Label note.",
            "test_features: [test_batch..., n_features]",
            "return[0]: [test_batch..., n_labels]",
            "return[1]: [test_batch..., n_labels]",
            "# Function note.",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("train", "features"),
                    make_shape_spec(varrank("train_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("train", "labels"),
                    make_shape_spec(varrank("train_batch"), "n_labels"),
                    note=ParsedNoteSpec("Label note."),
                ),
                make_arg_spec(
                    make_argument_ref("test_features"),
                    make_shape_spec(varrank("test_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 0),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 1),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
            ),
            (ParsedNoteSpec("Function note."),),
        ),
        """
        Predict mean and variance from some test features.
        First trains a model an `train`, then makes a prediction from the model and `test`.
        :param train: Data to train on.
        :param test_features: Features to make test prediction from.
        :returns: Model mean and variance prediction.
        """,
        """
        Predict mean and variance from some test features.
        First trains a model an `train`, then makes a prediction from the model and `test`.

        Function note.
        :param train:
            * **train.features** has shape [*train_batch*..., *n_features*].
            * **train.labels** has shape [*train_batch*..., *n_labels*]. Label note.

            Data to train on.
        :param test_features:
            * **test_features** has shape [*test_batch*..., *n_features*].

            Features to make test prediction from.
        :returns:
            * **return[0]** has shape [*test_batch*..., *n_labels*].
            * **return[1]** has shape [*test_batch*..., *n_labels*].

            Model mean and variance prediction.
        """,
    ),
    TestData(
        "funny_formatting_3",
        (
            "train.features: [train_batch..., n_features]",
            "train.labels: [train_batch..., n_labels]  # Label note.",
            "test_features: [test_batch..., n_features]",
            "return[0]: [test_batch..., n_labels]",
            "return[1]: [test_batch..., n_labels]",
            "# Function note.",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("train", "features"),
                    make_shape_spec(varrank("train_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("train", "labels"),
                    make_shape_spec(varrank("train_batch"), "n_labels"),
                    note=ParsedNoteSpec("Label note."),
                ),
                make_arg_spec(
                    make_argument_ref("test_features"),
                    make_shape_spec(varrank("test_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 0),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 1),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
            ),
            (ParsedNoteSpec("Function note."),),
        ),
        """Predict mean and variance from some test features.

        First trains a model an `train`, then makes a prediction from the model and `test`.
        :param train:
        Data to train on.
        And another line.
        :param test_features:
        Features to make test prediction from.
        And some more comment.
        :returns:
        Model mean and variance prediction.""",
        """Predict mean and variance from some test features.

        First trains a model an `train`, then makes a prediction from the model and `test`.

        Function note.
        :param train:
        * **train.features** has shape [*train_batch*..., *n_features*].
        * **train.labels** has shape [*train_batch*..., *n_labels*]. Label note.

        Data to train on.
        And another line.
        :param test_features:
        * **test_features** has shape [*test_batch*..., *n_features*].

        Features to make test prediction from.
        And some more comment.
        :returns:
        * **return[0]** has shape [*test_batch*..., *n_labels*].
        * **return[1]** has shape [*test_batch*..., *n_labels*].

        Model mean and variance prediction.""",
    ),
    TestData(
        "funny_formatting_4",
        (
            "train.features: [train_batch..., n_features]",
            "train.labels: [train_batch..., n_labels]  # Label note.",
            "test_features: [test_batch..., n_features]",
            "return[0]: [test_batch..., n_labels]",
            "return[1]: [test_batch..., n_labels]",
            "# Function note.",
        ),
        ParsedFunctionSpec(
            (
                make_arg_spec(
                    make_argument_ref("train", "features"),
                    make_shape_spec(varrank("train_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("train", "labels"),
                    make_shape_spec(varrank("train_batch"), "n_labels"),
                    note=ParsedNoteSpec("Label note."),
                ),
                make_arg_spec(
                    make_argument_ref("test_features"),
                    make_shape_spec(varrank("test_batch"), "n_features"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 0),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
                make_arg_spec(
                    make_argument_ref("return", 1),
                    make_shape_spec(varrank("test_batch"), "n_labels"),
                    note=None,
                ),
            ),
            (ParsedNoteSpec("Function note."),),
        ),
        """Predict mean and variance from some test features.

First trains a model an `train`, then makes a prediction from the model and `test`.
:param train:
Data to train on.
And another line.
:param test_features:
Features to make test prediction from.
And some more comment.
:returns:
Model mean and variance prediction.""",
        """Predict mean and variance from some test features.

First trains a model an `train`, then makes a prediction from the model and `test`.

Function note.
:param train:
* **train.features** has shape [*train_batch*..., *n_features*].
* **train.labels** has shape [*train_batch*..., *n_labels*]. Label note.

Data to train on.
And another line.
:param test_features:
* **test_features** has shape [*test_batch*..., *n_features*].

Features to make test prediction from.
And some more comment.
:returns:
* **return[0]** has shape [*test_batch*..., *n_labels*].
* **return[1]** has shape [*test_batch*..., *n_labels*].

Model mean and variance prediction.""",
    ),
]


@pytest.mark.parametrize("data", _TEST_DATA, ids=str)
def test_parse_function_spec(data: TestData) -> None:
    actual_spec = parse_function_spec(data.function_spec_strs, TestContext())
    assert data.expected_function_spec == actual_spec


@pytest.mark.parametrize("data", _TEST_DATA, ids=str)
def test_parse_and_rewrite_docstring(data: TestData) -> None:
    rewritten_docstring = parse_and_rewrite_docstring(
        data.doc, data.expected_function_spec, TestContext()
    )
    assert data.expected_doc == rewritten_docstring


@pytest.mark.parametrize("data", _TEST_DATA, ids=str)
def test_parse_and_rewrite_docstring__disable(data: TestData) -> None:
    set_rewrite_docstrings(None)

    rewritten_docstring = parse_and_rewrite_docstring(
        data.doc, data.expected_function_spec, TestContext()
    )
    assert data.doc == rewritten_docstring


@pytest.mark.parametrize(
    "spec,expected_message",
    [
        (
            "a [batch..., x]",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:     "a [batch..., x]"
                    ^
      Expected: integer (re=(?:[0-9])+)
""",
        ),
        (
            "a= [batch..., x]",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:            "a= [batch..., x]"
                         ^
      Expected one of: ":"
                       "."
                       "["
""",
        ),
        (
            "a: (batch..., x)",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:     "a: (batch..., x)"
                    ^
      Expected: "["
""",
        ),
        (
            "a: batch..., x]",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:     "a: batch..., x]"
                    ^
      Expected: "["
""",
        ),
        (
            "a: [batch... x]",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:            "a: [batch... x]"
                                     ^
      Expected one of: ","
                       "]"
""",
        ),
        (
            "a: [batch..., x",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:            "a: [batch..., x"
                                      ^
      Expected one of: ","
                       "..."
                       "]"
""",
        ),
        (
            "a: [, x]",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:            "a: [, x]"
                            ^
      Expected one of: variable name (re=(?:(?:[A-Z]|[a-z])|_)(?:(?:(?:[A-Z]|[a-z])|[0-9]|_))*)
                       "."
                       "..."
                       integer (re=(?:[0-9])+)
                       "None"
                       "]"
                       "*"
""",
        ),
        (
            "",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:            ""
                        ^
      Expected one of: variable name (re=(?:(?:[A-Z]|[a-z])|_)(?:(?:(?:[A-Z]|[a-z])|[0-9]|_))*)
                       "#"
""",
        ),
        (
            """
  a:
  [
    batch...
    x
  ]""",
            """
Unable to parse shape specification.
  check_shapes called at: __check_shapes_path_and_line__
    Argument number (0-indexed): 0
      Line:            "    x"
                            ^
      Expected one of: ","
                       "]"
""",
        ),
    ],
)
def test_parse_argument_spec__error(spec: str, expected_message: str) -> None:
    check_shapes_path_and_line = f"{__file__}:{current_line() + 2}"
    with pytest.raises(SpecificationParseError) as e:
        check_shapes(spec)
    (message,) = e.value.args
    expected_message = expected_message.replace(
        "__check_shapes_path_and_line__", check_shapes_path_and_line
    )
    assert expected_message == message


def test_parse_and_rewrite_docstring__error() -> None:
    # I don't actually know how to provoke an error from parsing the docstring.
    # The problem is that *any* string is allow as free-form documentation.
    # Update this test if you find a good example."
    assert True
