from typing import Iterable

from src.util import (
    generate_contractions,
    apply_rule_once,
    get_inverse_rep,
    get_most_shaveds,
    expand_notation,
    compress_notation,
    anti_cap,
)
from src.my_types import strings
from src.exceptions import IncompleteGroupException


class Group:
    """Represents mathematical groups, with the ability of inferring group structure from initial information.

    This class is designed to work with finite groups and uses a custom algorithm to deduce
    the group's structure. It tracks equivalences between representations of group elements and generates
    the full structure of the group, using the initial information and the axioms of group theory.

    Check the readme for a glossary of terminology, and for more information on how this algorithms works,
    or check the docstrings and comments in the code for more detail.
    """

    def __init__(
        self,
        initial_reps_elements: Iterable[strings] | None = None,
        name: str = "unnamed",
        sink_cap: int = 50,
    ) -> None:
        """Initiates a new Group object.

        We can immediately give it combinations of representations (reps) through `initial_reps_elements`,
        but we don't need to. We can also leave it empty and create a blank Group object.
        If we leave `evaluate` to be `True`, the structure of the group we're defining will be evaluated
        by first combining reduction rules, and then filling in the gaps.

        Parameters
        ----------
        initial_reps_elements : Iterable[strings] | None, optional
            Combinations of reps such that each combination defines an element, by default None
        name : str, optional
            The name of the group, which is just used for printing, by default "unnamed"
        sink_cap : int, optional
            The max amount of sinks we allow. Many options for `initial_reps_elements`
            would describe infinite groups. This implementation does not have a way to recognise this,
            so we can declare how many elements we expect the group to have, and abort
            when we find more sinks than this number during the process, by default 50
        evaluate : bool, optional
            Whether we immediately want to infer the group structure or not, by default True
        """
        self._name: str = name
        self._sink_cap: int = sink_cap

        # `self._reps_to_sinks` is gonna contain all reps of group elements we have encountered,
        # with a reference to the most reduced currently discovered rep
        self._reps_to_sinks: dict[str, str] = {}

        self._prime_reductibles: set[str] = set()
        self._generator_chars: set[str] = set()
        self._inverse_chars: set[str] = set()
        self._sinks: set[str] = set()

        if initial_reps_elements is None:
            initial_reps_elements = tuple()

        # Groups always contain an identity element
        self._integrate([""])

        for reps in initial_reps_elements:
            expanded_reps = [expand_notation(rep) for rep in reps]
            self._update_generator_chars(expanded_reps)
            self._integrate(expanded_reps)

        # Infer the group structure
        self.integrate_combined_prime_reductibles()
        self.fill_in_gaps()

    def _integrate(self, expanded_reps: strings) -> str:
        """Uses the information that all elements in `expanded_reps` describe the same group element.

        First of all we can equate all elements in `expanded_reps`, but maybe we already know how to recude
        some elements in `expanded_reps` with already established reps in `self._prime_reductibles`.
        Or maybe the equivalence of `expanded_reps` provides information on how to further reduce established
        representations that so far were considered prime.

        Parameters
        ----------
        expanded_reps : strings
            Collection of strings that all represent the same group element.

        Returns
        -------
        str
            The sink (most reduced currently established representation)
            for the element represented by `expanded_reps`.
        """
        all_relevant_equivalent_reps: set[str] = find_all_reachable_representations(
            expanded_reps, self._reps_to_sinks, self._prime_reductibles
        )

        most_reduced: str = min(all_relevant_equivalent_reps, key=self._rep_sort_key)

        for rep in all_relevant_equivalent_reps:
            # Establish equivalence between `rep` and `most_reduced` in `self._reps_to_sinks`
            self._set_entry(rep, most_reduced)

            # If `rep` is a sink, we can continue, because the rest of this block is only for
            # integrating shaved versions of `rep` and `most_reduced`
            if rep == most_reduced:
                continue

            most_shaveds: set[tuple[str, str]] = get_most_shaveds(rep, most_reduced)
            for most_shaved in most_shaveds:
                rep_shaved, most_reduced_shaved = most_shaved

                # If we can't shave, we have nothing new to integrate
                if rep == rep_shaved:
                    continue

                self._integrate([rep_shaved, most_reduced_shaved])

        return most_reduced

    def _set_entry(
        self, rep: str, new_reduced: str, process_for_primes: bool = True
    ) -> None:
        """Processes the information that `rep` can be reduced to `new_reduced`.

        In this function, the following things happen:
        - Check if `rep` is already in `self._reps_to_sinks`. If so, we have discovered
        that two reps that were both considered sinks so far, are actually equivalent.
        - Otherwise we register `rep` in `self._reps_to_sinks` with a reference to `new_reduced`.
        - If `rep` is not a sink, we process it as a potential prime reductible.

        Parameters
        ----------
        rep : str
            The representation to add to `self._reps_to_sinks`, and to process in the ways described above.
        new_reduced : str
            The potential sink state to have `rep` refer to in `self._reps_to_sinks`, if we haven't
            already established a better option.

        Raises
        ------
        MemoryError
            If we add `new_reduced` as a new sink, we check whether we haven't exceeded
            the number of sinks we wanna allow.
        """
        if rep in self._reps_to_sinks:
            known_reduced = self._reps_to_sinks[rep]
            if new_reduced == known_reduced:
                return

            # If `rep` is established but refers to a representation different from `new_reduced`,
            # we have discovered a new equivalence.
            most_reduced, less_reduced = sorted(
                (known_reduced, new_reduced), key=self._rep_sort_key
            )

            self._set_for_entries_with_value(less_reduced, most_reduced)
            # The rest of this function only deals with representations we haven't encountered before.
            return

        self._reps_to_sinks[rep] = new_reduced
        self._sinks.add(new_reduced)

        # If `rep` and `new_reduced` are equal, `rep` is a sink, and can't be used as a reduction rule
        if rep == new_reduced:
            if len(self._sinks) > self._sink_cap:
                raise MemoryError("Too many sinks")
            return

        if process_for_primes:
            self._process_as_potential_prime_reductible(rep)

    def _set_for_entries_with_value(self, old_value: str, new_value: str) -> None:
        """Changes all references to `old_value` in `self._reps_to_sinks` into references to `new_value`.

        Parameters
        ----------
        old_value : str
            The representation we're gonna replace with `new_value` in `self._reps_to_sinks`
        new_value : str
            The representation with which we're gonna replace `old_value`
        """
        if old_value == new_value or old_value not in self._sinks:
            return

        for unreduced, reduced in self._reps_to_sinks.items():
            if reduced == old_value:
                self._reps_to_sinks[unreduced] = new_value

                # `unreduced` might be part of `self._prime_reductibles`, but if it is, it now refers
                # to a different sink, so we should check if we need to update its status.
                self._process_as_potential_prime_reductible(unreduced)

        self._sinks.remove(old_value)
        self._sinks.add(new_value)

    def _process_as_potential_prime_reductible(self, rep: str) -> None:
        """Checks if `rep` is prime reductible, and if so, processes it as such.

        This means we add it to `self._prime_reductibles`, and then we check for all previously established
        prime reductibles whether they still are, and if not, we remove them from `self._prime_reductibles`.

        Parameters
        ----------
        rep : str
            Reprenestation to be processed.
        """
        if not self._should_be_prime_reductible(rep):
            return

        self._prime_reductibles.add(rep)

        # Check whether the other reps in `self._prime_reductibles` should remain in there
        for established_prime in tuple(self._prime_reductibles):
            # If `rep` is not more reduced than `established_prime`, we can't possibly reduce
            if self._rep_sort_key(rep) >= self._rep_sort_key(established_prime):
                continue

            if not self._should_be_prime_reductible(established_prime):
                self._prime_reductibles.remove(established_prime)

    def _should_be_prime_reductible(self, rep: str) -> bool:
        """Assesses whether `rep` is a prime reductible for the current state of this `Group` object.

        If we can not reduce `rep` to its associated sink in `self._reps_to_sinks` by using the currently
        established `self._prime_reductibles`, it should itself be considered a prime reductible.

        Parameters
        ----------
        rep : str
            The representation that might be a prime reductible.

        Returns
        -------
        bool
            Whether `rep` is a prime reductible.
        """
        # Don't use `rep` to try and reduce `rep`
        other_prime_reductibles = self._prime_reductibles - {rep}
        allowed_references = {
            prime: self._reps_to_sinks[prime] for prime in other_prime_reductibles
        }

        reachable_representations_from_rep = find_all_reachable_representations(
            (rep,),
            allowed_references,
            other_prime_reductibles,
        )

        should_be_prime = (
            self._reps_to_sinks[rep] not in reachable_representations_from_rep
        )
        return should_be_prime

    def _update_generator_chars(self, reps: strings) -> None:
        """Adds all individual characters in the elements in `reps` to `self._generator_chars`.

        If it is a new generator character, we check if its inverse is in `self._generator_chars` as well,
        represented by the opposite case of the character (so inverse of H := h, and inverse of h := H).
        We then also integrate the rule that Hh == hH == e.

        Parameters
        ----------
        reps : strings
            The representations from which to extract the individual characters.
        """
        for g in "".join(reps):
            # If we have already established `g` as a generator or inverse character, we continue
            if g in self._generator_chars or g in self._inverse_chars:
                continue

            # Otherwise we add it now
            self._generator_chars.add(g)

            # And we'll add the inverse to our inverse set, and establish their relation
            g_inverse = anti_cap(g)
            self._inverse_chars.add(g_inverse)
            self._integrate((g + g_inverse, g_inverse + g, ""))

    def _determine_first_element_with_incomplete_image(self) -> tuple[str, str] | None:
        """Some elements might not have a complete image.

        This function will check all established sinks `sink`, and all generator chars `g`,
        to see if we have established the representations `sink` + `g`. If not, we don't establish it now,
        but return the combination

        Returns
        -------
        tuple[str, str] | None
            The combination of `sink` and `g`, or `None` if all compositions of sinks and generator chars
            have already been established.
        """
        for sink in self._sinks:
            for generator_char in self._generator_chars:
                if sink + generator_char not in self._reps_to_sinks:
                    return (sink, generator_char)

        return None

    def _rep_sort_key(self, s: str) -> tuple[int, int, str]:
        """A sort key that will sort strings based on length, and then on the value itself.

        Parameters
        ----------
        s : str
            The string we want compare to other strings.

        Returns
        -------
        tuple[int, str]
            A tuple containing the length of `s`, and `s` itself secundarily.
        """
        return (self._count_inverse_characters(s), len(s), s)

    def _count_inverse_characters(self, s: str) -> int:
        """Counts how many occurences of inverse characters are in `s`

        Parameters
        ----------
        s : str
            String with potential inverse characters.

        Returns
        -------
        int
            Number of inverse characters.
        """
        return sum(1 for char in s if char in self._inverse_chars)

    def __str__(self) -> str:
        """See `self.__repr__`"""
        return self.__repr__()

    def __format__(self, _: str) -> str:
        """See `self.__repr__`"""
        return self.__repr__()

    def __repr__(self) -> str:
        """The string representation of a Group object contains the following:

        - The name of the group
        - A list of its sinks
        - A list of its prime reductibles
        - Whether the group is complete, meaning its structue is fully established

        Returns
        -------
        str
            The string representation of this Group object
        """
        name_string = f"Group with name: {self._name}"

        sinks_sorted = list(sorted(self._sinks, key=self._rep_sort_key))
        sinks_compressed = [compress_notation(sink) for sink in sinks_sorted]
        sinks_string = f"Sinks:\n{sinks_compressed}"

        prime_reductibles_sorted = list(
            sorted(self._prime_reductibles, key=self._rep_sort_key)
        )
        prime_reductibles_compressed = [
            f"{compress_notation(prime)} -> {compress_notation(self._reps_to_sinks[prime])}"
            for prime in prime_reductibles_sorted
        ]
        prime_reductibles_string = (
            f"Prime reductibles:\n{'\n'.join(prime_reductibles_compressed)}"
        )

        sink_g = self._determine_first_element_with_incomplete_image()
        completeness_string = (
            "Complete" + (" (trivially)" if len(self._sinks) == 1 else "")
            if sink_g is None
            else f"Incomplete, missing {compress_notation(''.join(sink_g))}"
        )

        return "\n\n".join(
            (name_string, sinks_string, prime_reductibles_string, completeness_string)
        )

    def __call__(self, *reps: str) -> None:
        """Integrates `reps`, and prints the most reduced representation for it, and the group itself."""
        expanded_reps = [expand_notation(rep) for rep in reps]
        self._update_generator_chars(expanded_reps)
        most_reduced = self._integrate(expanded_reps)
        print(f"Most reduced: {compress_notation(most_reduced)}")
        print(self)

    # Everything below this point is public, and can be called externally

    def integrate_combined_prime_reductibles(self) -> None:
        """Takes pairs of `self._prime_reductibles` and integrates their combinations.

        An example could be we have `self._prime_reductibles` := {"LH", "HR"}
        We can get the combination "LHR" (see `generate_contractions`). This can be reduced in two ways,
        leading to two potentially different reduced forms, which we can then integrate
        as representations of the same element, hopefully leading to the discovery of equivalences.
        """
        while not self.is_complete():
            sorted_prime_reductibles: list[str] = sorted(
                self._prime_reductibles, key=self._rep_sort_key
            )

            # Check for all combinations of prime reductibles, including reductibles with themselves
            for i, s1 in enumerate(sorted_prime_reductibles):
                for s2 in sorted_prime_reductibles[i:]:
                    # We might already have removed one of them
                    if (
                        s1 not in self._prime_reductibles
                        or s2 not in self._prime_reductibles
                    ):
                        continue
                    contractions: set[str] = generate_contractions(s1, s2)
                    for contraction in contractions:
                        self._integrate((contraction,))

            # If we did not find any new primes, we have nothing left to try
            if set(sorted_prime_reductibles) == self._prime_reductibles:
                break

    def fill_in_gaps(self) -> None:
        """Add representations for combinations of sinks and generator chars that haven't been established."""
        while (
            sink_and_g := self._determine_first_element_with_incomplete_image()
        ) is not None:
            sink, g = sink_and_g
            self._integrate((sink + g,))

    def is_complete(self) -> bool:
        """True if there are no more combinations of sinks and generator chars that haven't been established.

        Returns
        -------
        bool
            ...
        """
        return self._determine_first_element_with_incomplete_image() is None

    def get_sink_for(self, s: str) -> str:
        """If the `Group` object is complete, this will find the sink of `s` very quickly.

        This function wouldn't find all possible equivalences if we haven't already discovered them,
        like we would need if we are still trying to infer the group structure.

        Parameters
        ----------
        s : str
            Representation to reduce

        Returns
        -------
        str
            Sink for `s`

        Raises
        ------
        IncompleteGroupException
            If our group structure is not complete, we want to first complete it.
        """
        if not self.is_complete():
            raise IncompleteGroupException()

        # This function uses recursion, but we don't want to check `self._is_complete()`
        # every recursive call, so once we've asserted completeness, we can just use this nested function
        def get_sink_rec(s_expanded: str) -> str:
            # If we've already encountered `s`, we can just return its associated sink
            if s_expanded in self._reps_to_sinks:
                sink = self._reps_to_sinks[s_expanded]
                return sink

            # Otherwise we'll split `s` in two, and reduce the halves individually
            half_len: int = len(s_expanded) // 2
            first_half: str = get_sink_rec(s_expanded[:half_len])
            second_half: str = get_sink_rec(s_expanded[half_len:])
            reduced = first_half + second_half  # equivalent to `s`

            if reduced in self._reps_to_sinks:
                sink = self._reps_to_sinks[reduced]

                # Cache the equivalence
                self._set_entry(s_expanded, sink, False)
                return sink

            # If this still doesn't work, we can integrate `reduced`
            sink = self._integrate((reduced,))
            self._set_entry(s_expanded, sink, False)
            return sink

        s_expanded = expand_notation(s)
        sink = get_sink_rec(s_expanded)
        return sink

    def get_inverse_of(self, s: str) -> str:
        """If the `Group` object is complete, this will find the inverse of `s`.

        Parameters
        ----------
        s : str
            Rep to invert.

        Returns
        -------
        str
            Inverse.
        """
        inverted_rep = get_inverse_rep(s)
        return self.get_sink_for(inverted_rep)

    @property
    def nr_of_explored_reps(self) -> int:
        """Number of representations we've encountered during inferring the structure of the group.

        Returns
        -------
        int
            ...
        """
        return len(self._reps_to_sinks)


def find_all_reachable_representations(
    reps: strings,
    reps_to_sinks: dict[str, str],
    prime_reductibles: set[str],
    all_equivalent_reps: set[str] | None = None,
) -> set[str]:
    """Recursively searches for all accessible reduced versions of `reps` with the provided inputs.

    This is done by looping over all `rep` in `reps`, and checking whether we've encountered it before
    during this recurive search, or whether it exists in `reps_to_sinks`. If so, we can assume equivalence
    to the sink representation it's referring to. If not, we have to expand on it.
    To do so, we use `prime_reductibles`, to see if we can reduce `rep` to other equivalent representations.
    This is done recursively, such that by the end, we will have collected all new equivalent representations,
    plus the sink representations of the ones we have seen before. This might include more than one sink state.
    If that if the case, we have discovered that two former sink states are actually different representations
    for the same element, but this function doesn't process that information.


    Parameters
    ----------
    reps : strings
        Some collection of equivalent representations.
    reps_to_sinks : dict[str, str]
        Already assumed equivalences.
    prime_reductibles : set[str]
        When reducing representations in `reps`, only these reductibles will be used.
    all_equivalent_reps : set[str] | None, optional
        Representations that we have found to be equivalent in this recursive search, by default None.

    Returns
    -------
    set[str]
        The union of the input, all possible reduced representations that we haven't seen before,
        and the sink representations of the ones we have seen before.
    """
    if all_equivalent_reps is None:
        all_equivalent_reps = set()

    for rep in reps:
        if rep in all_equivalent_reps:
            continue

        all_equivalent_reps.add(rep)

        # If `rep` already has an associated sink, go straight to the sink
        if rep in reps_to_sinks:
            all_equivalent_reps.add(reps_to_sinks[rep])
            continue

        # Otherwise we try to recude `rep` with `prime_reductibles`
        for left in prime_reductibles:
            right = reps_to_sinks[left]
            reps_after_application = apply_rule_once(left, right, rep)

            find_all_reachable_representations(
                reps_after_application,
                reps_to_sinks,
                prime_reductibles,
                all_equivalent_reps,
            )

    return all_equivalent_reps
