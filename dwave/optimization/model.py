# Copyright 2024 D-Wave Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Nonlinear models are especially suited for use with decision variables that
represent a common logic, such as subsets of choices or permutations of ordering.
For example, in a
`traveling salesperson problem <https://en.wikipedia.org/wiki/Travelling_salesman_problem>`_
permutations of the variables representing cities can signify the order of the
route being optimized and in a
`knapsack problem <https://en.wikipedia.org/wiki/Knapsack_problem>`_ the
variables representing items can be divided into subsets of packed and not
packed.
"""

import contextlib
import tempfile

from dwave.optimization._graph import ArraySymbol, _Graph, Symbol

__all__ = ["Model"]


@contextlib.contextmanager
def locked(model):
    """Context manager that hold a locked model and unlocks it when the context is exited."""
    try:
        yield
    finally:
        model.unlock()


class Model(_Graph):
    """Nonlinear model.

    The nonlinear model represents a general optimization problem with an
    :term:`objective function` and/or constraints over variables of various
    types.

    The :class:`.Model` class can contain this model and its methods provide
    convenient utilities for working with representations of a problem.

    Examples:
        This example creates a model for a
        :class:`flow-shop-scheduling <dwave.optimization.generators.flow_shop_scheduling>`
        problem with two jobs on three machines.

        >>> from dwave.optimization.generators import flow_shop_scheduling
        ...
        >>> processing_times = [[10, 5, 7], [20, 10, 15]]
        >>> model = flow_shop_scheduling(processing_times=processing_times)
    """

    def __init__(self):
        pass

    def binary(self, shape=None):
        r"""Create a binary symbol as a decision variable.

        Args:
            shape: Shape of the binary array to create.

        Returns:
            A binary symbol.

        Examples:
            This example creates a :math:`1 \times 20`-sized binary symbol.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> x = model.binary((1,20))
        """
        from dwave.optimization.symbols import BinaryVariable  # avoid circular import
        return BinaryVariable(self, shape)

    def constant(self, array_like):
        r"""Create a constant symbol.

        Args:
            array_like: An |array-like|_ representing a constant. Can be a scalar
                or a NumPy array. If the array's ``dtype`` is ``np.double``, the
                array is not copied.

        Returns:
            A constant symbol.

        Examples:
            This example creates a :math:`1 \times 4`-sized constant symbol
            with the specified values.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> time_limits = model.constant([10, 15, 5, 8.5])
        """
        from dwave.optimization.symbols import Constant  # avoid circular import
        return Constant(self, array_like)

    def disjoint_bit_sets(self, primary_set_size, num_disjoint_sets):
        """Create a disjoint-sets symbol as a decision variable.

        Divides a set of the elements of ``range(primary_set_size)`` into
        ``num_disjoint_sets`` ordered partitions, stored as bit sets (arrays
        of length ``primary_set_size``, with ones at the indices of elements
        currently in the set, and zeros elsewhere). The ordering of a set is
        not semantically meaningful.

        Also creates from the symbol ``num_disjoint_sets`` extra successors
        that output the disjoint sets as arrays.

        Args:
            primary_set_size: Number of elements in the primary set that are
                partitioned into disjoint sets. Must be non-negative.
            num_disjoint_sets: Number of disjoint sets. Must be positive.

        Returns:
            A tuple where the first element is the disjoint-sets symbol and
            the second is a set of its newly added successors.

        Examples:
            This example creates a symbol of 10 elements that is divided
            into 4 sets.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> parts_set, parts_subsets = model.disjoint_bit_sets(10, 4)
        """

        from dwave.optimization.symbols import DisjointBitSets, DisjointBitSet  # avoid circular import
        main = DisjointBitSets(self, primary_set_size, num_disjoint_sets)
        sets = tuple(DisjointBitSet(main, i) for i in range(num_disjoint_sets))
        return main, sets

    def disjoint_lists(self, primary_set_size, num_disjoint_lists):
        """Create a disjoint-lists symbol as a decision variable.

        Divides a set of the elements of ``range(primary_set_size)`` into
        ``num_disjoint_lists`` ordered partitions.

        Also creates ``num_disjoint_lists`` extra successors from the
        symbol that output the disjoint lists as arrays.

        Args:
            primary_set_size: Number of elements in the primary set to
                be partitioned into disjoint lists.
            num_disjoint_lists: Number of disjoint lists.

        Returns:
            A tuple where the first element is the disjoint-lists symbol
            and the second is a list of its newly added successor nodes.

        Examples:
            This example creates a symbol of 10 elements that is divided
            into 4 lists.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> destinations, routes = model.disjoint_lists(10, 4)
        """
        from dwave.optimization.symbols import DisjointLists, DisjointList  # avoid circular import
        main = DisjointLists(self, primary_set_size, num_disjoint_lists)
        lists = [DisjointList(main, i) for i in range(num_disjoint_lists)]
        return main, lists

    def feasible(self, index: int = 0):
        """Check the feasibility of the state at the input index.

        Args:
            index: index of the state to check for feasibility.

        Returns:
            Feasibility of the state.

        Examples:
            This example demonstrates checking the feasibility of a simple model with
            feasible and infeasible states.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> b = model.binary()
            >>> model.add_constraint(b) # doctest: +ELLIPSIS
            <dwave.optimization.BinaryVariable at ...>
            >>> model.states.resize(2)
            >>> b.set_state(0, 1) # Feasible
            >>> b.set_state(1, 0) # Infeasible
            >>> with model.lock():
            ...     model.feasible(0)
            True
            >>> with model.lock():
            ...     model.feasible(1)
            False
        """
        return all(sym.state(index) for sym in self.iter_constraints())

    def integer(self, shape=None, lower_bound=None, upper_bound=None):
        r"""Create an integer symbol as a decision variable.

        Args:
            shape: Shape of the integer array to create.

            lower_bound: Lower bound for the symbol, which is the
                smallest allowed integer value. If None, the default
                value is used.
            upper_bound: Upper bound for the symbol, which is the
                largest allowed integer value. If None, the default
                value is used.

        Returns:
            An integer symbol.

        Examples:
            This example creates a :math:`20 \times 20`-sized integer symbol.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> i = model.integer((20,20), lower_bound=-100, upper_bound=100)
        """
        from dwave.optimization.symbols import IntegerVariable  # avoid circular import
        return IntegerVariable(self, shape, lower_bound, upper_bound)

    def list(self, n: int):
        """Create a list symbol as a decision variable.

        Args:
            n: Values in the list are permutations of ``range(n)``.

        Returns:
            A list symbol.

        Examples:
            This example creates a list symbol of 200 elements.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> routes = model.list(200)
        """
        from dwave.optimization.symbols import ListVariable  # avoid circular import
        return ListVariable(self, n)

    def lock(self):
        """Lock the model.

        No new symbols can be added to a locked model.

        Returns:
            A context manager. If the context is subsequently exited then the
            :meth:`.unlock` will be called.

        See also:
            :meth:`.is_locked`, :meth:`.unlock`

        Examples:
            This example checks the status of a model after locking it and
            subsequently unlocking it.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> i = model.integer(20, upper_bound=100)
            >>> cntx = model.lock()
            >>> model.is_locked()
            True
            >>> model.unlock()
            >>> model.is_locked()
            False

            This example locks a model temporarily with a context manager.

            >>> model = Model()
            >>> with model.lock():
            ...     # no nodes can be added within the context
            ...     print(model.is_locked())
            True
            >>> model.is_locked()
            False
        """
        super().lock()
        return locked(self)

    def quadratic_model(self, x, quadratic, linear=None):
        """Create a quadratic model from an array and a quadratic model.

        Args:
            x: An array.

            quadratic: Quadratic values for the quadratic model.

            linear: Linear values for the quadratic model.

        Returns:
            A quadratic model.

        Examples:
            This example creates a quadratic model.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> x = model.binary(3)
            >>> Q = {(0, 0): 0, (0, 1): 1, (0, 2): 2, (1, 1): 1, (1, 2): 3, (2, 2): 2}
            >>> qm = model.quadratic_model(x, Q)

        """
        from dwave.optimization.symbols import QuadraticModel
        return QuadraticModel(x, quadratic, linear)

    def set(self, n, min_size=0, max_size=None):
        """Create a set symbol as a decision variable.

        Args:
            n: Values in the set are subsets of ``range(n)``.
            min_size: Minimum set size. Defaults to ``0``.
            max_size: Maximum set size. Defaults to ``n``.

        Returns:
            A set symbol.

        Examples:
            This example creates a set symbol of up to 4 elements
            with values between 0 to 99.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> destinations = model.set(100, max_size=4)
        """
        from dwave.optimization.symbols import SetVariable  # avoid circular import
        return SetVariable(self, n, min_size, n if max_size is None else max_size)

    def to_file(self, **kwargs):
        """Serialize the model to a new file-like object.

        See also:
            :meth:`.into_file`, :meth:`.from_file`
        """
        file = tempfile.TemporaryFile(mode="w+b")
        self.into_file(file, **kwargs)
        file.seek(0)
        return file

    def to_networkx(self):
        """Convert the model to a NetworkX graph.

        Returns:
            A :obj:`NetworkX <networkx:networkx.MultiDiGraph>` graph.

        Examples:
            This example converts a model to a graph.

            >>> from dwave.optimization.model import Model
            >>> model = Model()
            >>> one = model.constant(1)
            >>> two = model.constant(2)
            >>> i = model.integer()
            >>> model.minimize(two * i - one)
            >>> G = model.to_networkx()  # doctest: +SKIP

            One advantage of converting to NetworkX is the wide availability
            of drawing tools. See NetworkX's
            `drawing <https://networkx.org/documentation/stable/reference/drawing.html>`_
            documentation.

            This example uses `DAGVIZ <https://wimyedema.github.io/dagviz/>`_ to
            draw the NetworkX graph created in the example above.

            >>> import dagviz                      # doctest: +SKIP
            >>> r = dagviz.render_svg(G)           # doctest: +SKIP
            >>> with open("model.svg", "w") as f:  # doctest: +SKIP
            ...     f.write(r)

            This creates the following image:

            .. figure:: /_images/to_networkx_example.svg
               :width: 500 px
               :name: dwave-optimization-to-networkx-example
               :alt: Image of NetworkX Directed Graph

        """
        import networkx

        G = networkx.MultiDiGraph()

        # Add the symbols, in order if we happen to be topologically sorted
        G.add_nodes_from(repr(symbol) for symbol in self.iter_symbols())

        # Sanity check. If several nodes map to the same symbol repr we'll see
        # too few nodes in the graph
        if len(G) != self.num_symbols():
            raise RuntimeError("symbol repr() is not unique to the underlying node")

        # Now add the edges
        for symbol in self.iter_symbols():
            for successor in symbol.iter_successors():
                G.add_edge(repr(symbol), repr(successor))

        # Sanity check again. If the repr of symbols isn't unique to the underlying
        # node then we'll see too many nodes in the graph here
        if len(G) != self.num_symbols():
            raise RuntimeError("symbol repr() is not unique to the underlying node")

        # Add the objective if it's present. We call it "minimize" to be
        # consistent with the minimize() function
        if self.objective is not None:
            G.add_edge(repr(self.objective), "minimize")

        # Likewise if we have constraints, add a special node for them
        for symbol in self.iter_constraints():
            G.add_edge(repr(symbol), "constraint(s)")

        return G
