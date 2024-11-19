from typing import Iterable, Any, Callable

from src.util import (
    generate_contractions,
    apply_rule_once,
    get_most_shaveds,
    expand_notation,
    compress_notation,
    anti_cap,
)
from src.my_types import strings


def dict_sort_key_len(s: str) -> tuple[int, str]:
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
    return (len(s), s)


def dict_sort_key_default(s: str) -> str:
    """The default sort key for strings.

    Parameters
    ----------
    s : str
        The string we want compare to other strings.

    Returns
    -------
    str
        Just the string itself.
    """
    return s


# The sort key we will use when integrating new representations
INTEGRATE_KEY: Callable[[str], Any] = dict_sort_key_len

# The sort key we will use when printing a collection of representations
PRINT_KEY: Callable[[str], Any] = dict_sort_key_default


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
        evaluate: bool = True,
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
        self.name: str = name
        self.sink_cap: int = sink_cap

        # `self.reps_to_sinks` is gonna contain all reps of group elements we have encountered,
        # with a reference to the most reduced currently discovered rep
        self.reps_to_sinks: dict[str, str] = {}

        # `self.prime_reductibles` is gonna contain all reps that can be reduced to a sink,
        # that wouldn't otherwise be reachable with the established prime reductibles
        self.prime_reductibles: set[str] = set()

        # `self.generator_chars` is gonna contain all individual characters we encounter
        self.generator_chars: set[str] = set()

        # `self.sinks` is gonna contain all reps that can't be reduced further
        self.sinks: set[str] = set()

        if initial_reps_elements is None:
            initial_reps_elements = tuple()

        # Groups always contain an identity element
        self._integrate([""])

        # We process all combinations of representations in `initial_reps_elements`
        for reps in initial_reps_elements:
            # This function could be called externally with compressed notation
            expanded_reps = [expand_notation(rep) for rep in reps]
            self._integrate(expanded_reps)

        # If we should evaluate, we will try and find the full structure of the group here
        if evaluate:
            self.integrate_combined_prime_reductibles()
            self.fill_in_gaps()

    def _integrate(self, expanded_reps: strings) -> str:
        """Uses the information that all elements in `expanded_reps` describe the same group element.

        First of all we can equate all elements in `expanded_reps`, but maybe we already know how to recude
        some elements in `expanded_reps` with already established reps in `self.prime_reductibles`.
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
        # Update generator chars
        self._update_generator_chars(expanded_reps)

        # Start recursion to get all currently reachable equivalent representations
        all_relevant_equivalent_reps: set[str] = find_all_reachable_representations(
            expanded_reps, self.reps_to_sinks, self.prime_reductibles
        )

        # Determine the most reduced one
        most_reduced: str = min(all_relevant_equivalent_reps, key=INTEGRATE_KEY)

        for rep in all_relevant_equivalent_reps:
            # Establish equivalence between `rep` and `most_reduced` in `self.reps_to_sinks`
            self._set_entry(rep, most_reduced)

            # If `rep` is a sink, we can continue, because the rest of this block is only for
            # integrating shaved versions of `rep` and `most_reduced`
            if rep == most_reduced:
                continue

            # Get shaved versions
            most_shaveds: set[tuple[str, str]] = get_most_shaveds(rep, most_reduced)
            for most_shaved in most_shaveds:
                rep_shaved, most_reduced_shaved = most_shaved

                # If we can't shave, we have nothing new to integrate
                if rep == rep_shaved:
                    continue

                # Integrate the shaved versions
                self._integrate([rep_shaved, most_reduced_shaved])

        # Return the most reduced representation of the input
        return most_reduced

    def _set_entry(self, rep: str, new_reduced: str) -> None:
        """Processes the information that `rep` can be reduced to `new_reduced`.

        In this function, the following things happen:
        - Check if `rep` is already in `self.reps_to_sinks`. If so, we have discovered
        that two reps that were both considered sinks so far, are actually equivalent.
        - Otherwise we register `rep` in `self.reps_to_sinks` with a reference to `new_reduced`.
        - If `rep` is not a sink, we process it as a potential prime reductible.

        Parameters
        ----------
        rep : str
            The representation to add to `self.reps_to_sinks`, and to process in the ways described above.
        new_reduced : str
            The potential sink state to have `rep` refer to in `self.reps_to_sinks`, if we haven't
            already established a better option.

        Raises
        ------
        MemoryError
            If we add `new_reduced` as a new sink, we check whether we haven't exceeded
            the number of sinks we wanna allow.
        """
        if rep in self.reps_to_sinks:
            # If `rep` is already established with the same reduced representation `new_reduced`,
            # we don't need to do anything and can return
            known_reduced = self.reps_to_sinks[rep]
            if new_reduced == known_reduced:
                return

            # If `rep` is established but refers to a representation different from `new_reduced`,
            # we have discovered a new equivalence.
            # We see which of the newly equivalent reduced versions is the most reduced
            most_reduced, less_reduced = sorted(
                (known_reduced, new_reduced), key=INTEGRATE_KEY
            )

            # Then we change all current refs to `less_reduced` into refs to `most_reduced`, and return,
            # because the rest of this function deals with representations we haven't encountered before.
            self._set_for_entries_with_value(less_reduced, most_reduced)
            return

        # If `rep` is not already established, we just add it to `self.reps_to_sinks` with a ref to `new_reduced`
        self.reps_to_sinks[rep] = new_reduced

        # `new_reduced` has to be a sink. it might be an established sink, but `self.sinks` is a set,
        # so we don't have to worry about duplicates and just add it in case it's new
        self.sinks.add(new_reduced)

        # If `rep` and `new_reduced` are equal, `rep` is a sink, and can't be used as a reduction rule
        if rep == new_reduced:
            # We also have to check if we're not over our cap. This is here because i haven't written
            # anything to handle infinite groups and i don't like getting stuck in loops
            if len(self.sinks) > self.sink_cap:
                raise MemoryError("Too many sinks")
            return

        # If `rep` and `new_reduced` are not equal, it can potentially be used as a prime reductible,
        # and we'll have to do some checks
        self._process_as_potential_prime_reductible(rep)

    def _set_for_entries_with_value(self, old_value: str, new_value: str) -> None:
        """Changes all references to `old_value` in `self.reps_to_sinks` into references to `new_value`.

        Parameters
        ----------
        old_value : str
            The representation we're gonna replace with `new_value` in `self.reps_to_sinks`
        new_value : str
            The representation with which we're gonna replace `old_value`
        """
        # If the old reference and the new reference are the same, or `old_value` is
        # not currently a sink, we don't have to do anything.
        # It is easier to do this check here, otherwise it has to happen in multiple other places
        if old_value == new_value or old_value not in self.sinks:
            return

        # If they're not the same and `old_value` is currently a sink,
        # we change every ref to `old_value` into a ref to `new_value`
        for unreduced, reduced in self.reps_to_sinks.items():
            if reduced == old_value:
                self.reps_to_sinks[unreduced] = new_value

                # `unreduced` might be part of `self.prime_reductibles`, but if it is, it now refers
                # to a different sink, so we should check if we need to update its status.
                self._process_as_potential_prime_reductible(unreduced)

        # `old_value` used to be a sink, but it's not anymore, and `new_value` now is
        self.sinks.remove(old_value)
        self.sinks.add(new_value)

    def _process_as_potential_prime_reductible(self, rep: str) -> None:
        """Checks if `rep` is prime reductible, and if so, processes it as such.

        This means we add it to `self.prime_reductibles`, and then we check for all previously established
        prime reductibles whether they still are, and if not, we remove them from `self.prime_reductibles`.

        Parameters
        ----------
        rep : str
            Reprenestation to be processed.
        """
        # If `rep` is not a prime reductible, we don't need to do anything
        if not self._should_be_prime_reductible(rep):
            return

        # If `rep` is a prime reductible, we add it to `self.prime_reductibles`
        self.prime_reductibles.add(rep)

        # Then we check whether the other reps in `self.prime_reductibles` should remain in there
        for established_prime in tuple(self.prime_reductibles):
            # If `rep` is less reduced than `established_prime`, we can't possibly reduce
            if INTEGRATE_KEY(rep) >= INTEGRATE_KEY(established_prime):
                continue

            # Otherwise, if we find `estblished_prime` to be redundant, we remove it
            if not self._should_be_prime_reductible(established_prime):
                self.prime_reductibles.remove(established_prime)

    def _should_be_prime_reductible(self, rep: str) -> bool:
        """Assesses whether `rep` is a prime reductible for the current state of this `Group` object.

        If we can not reduce `rep` to its associated sink in `self.reps_to_sinks` by using the currently
        established `self.prime_reductibles`, it should itself be considered a prime reductible.

        Parameters
        ----------
        rep : str
            The representation that might be a prime reductible.

        Returns
        -------
        bool
            Whether `rep` is a prime reductible.
        """
        # We'll have to check whether we can reduce `rep`, but since we don't want to use `rep`
        # to reduce `rep`, and `rep` might already be part of `self.prime_reductibles`, we should
        # create a copy that doesn't contain `rep`
        other_prime_reductibles = self.prime_reductibles - {rep}

        # We're only gonna use `other_prime_reductibles` in the reduction of `rep`
        allowed_references = {
            prime: self.reps_to_sinks[prime] for prime in other_prime_reductibles
        }

        # We assess which representations we can find from `rep` using just these reductibles
        reachable_representations_from_rep = find_all_reachable_representations(
            (rep,),
            allowed_references,
            other_prime_reductibles,
        )

        # `rep` should be a prime reductible, iff we can not reduce it to its associated sink
        should_be_prime = (
            self.reps_to_sinks[rep] not in reachable_representations_from_rep
        )
        return should_be_prime

    def _update_generator_chars(self, reps: strings) -> None:
        """Adds all individual characters in the elements in `reps` to `self.generator_chars`.

        If it is a new generator character, we check if its inverse is in `self.generator_chars` as well,
        represented by the opposite case of the character (so inverse of H := h, and inverse of h := H).
        We then also integrate the rule that Hh == hH == e.

        Parameters
        ----------
        reps : strings
            The representations from which to extract the individual characters.
        """
        # We create a set to only consider individual characters
        generator_chars_in_reps = set("".join([rep for rep in reps]))

        for g in generator_chars_in_reps:
            # If we have already established `g` as a generator character, we can continue to the next
            if g in self.generator_chars:
                continue

            # Otherwise we add it now
            self.generator_chars.add(g)

            # And then we check if we've encountered the character with opposite case,
            # which represents the inverse of `g`, and integrate the inverse rule
            g_inverse = anti_cap(g)
            if g_inverse in self.generator_chars:
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
        # The sinks represent all elements we're aware of
        for sink in self.sinks:
            # The generator chars represent all shortestly representable group elements
            for generator_char in self.generator_chars:
                # If we find a sink, such that if we add a generator char to it, we don't recognise the result
                # we don't know this composition yet, and we don't know that we have discovered the full structure yet
                if sink + generator_char not in self.reps_to_sinks:
                    # So we return the missing link
                    return (sink, generator_char)

        # If all of the structure is established, we return `None`
        return None

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
        name_string = f"Group with name: {self.name}"

        sinks_sorted = list(sorted(self.sinks, key=PRINT_KEY))
        sinks_expanded = [compress_notation(sink) for sink in sinks_sorted]
        sinks_string = f"Sinks:\n{sinks_expanded}"

        prime_reductibles_sorted = list(sorted(self.prime_reductibles, key=PRINT_KEY))
        prime_reductibles_expanded = [
            f"{compress_notation(prime)} -> {compress_notation(self.reps_to_sinks[prime])}"
            for prime in prime_reductibles_sorted
        ]
        prime_reductibles_string = (
            f"Prime reductibles:\n{'\n'.join(prime_reductibles_expanded)}"
        )

        sink_g = self._determine_first_element_with_incomplete_image()
        completeness_string = (
            "Complete" + (" (trivially)" if len(self.sinks) == 1 else "")
            if sink_g is None
            else f"Incomplete, missing {''.join(sink_g)}"
        )

        return "\n\n".join(
            (name_string, sinks_string, prime_reductibles_string, completeness_string)
        )

    def integrate_combined_prime_reductibles(self) -> None:
        """Takes pairs of `self.prime_reductibles` and integrates their combinations.

        An example could be we have `self.prime_reductibles` := {"LH", "HR"}
        We can get the combination "LHR" (see `generate_contractions`). This can be reduced in two ways,
        leading to two potentially different reduced forms, which we can then integrate
        as representations of the same element, hopefully leading to the discovery of equivalences.
        """
        while not self.is_complete():
            # We loop over the rules in order, this is not essential but it's nice to keep track
            # And we need to make a copy for the loop anyway
            sorted_prime_reductibles: tuple[str, ...] = tuple(
                sorted(self.prime_reductibles, key=INTEGRATE_KEY)
            )

            # We check for all combinations of prime reductibles, including reductibles with themselves,
            # But we only have to do this once per combination, so we only look for pairs of reductibles
            # Where one comes before the other (or where they're the same)
            for i, s1 in enumerate(sorted_prime_reductibles):
                for s2 in sorted_prime_reductibles[i:]:
                    contractions: set[str] = generate_contractions(s1, s2)
                    for contraction in contractions:
                        # We integrate for all contractions of `s1` and `s2`
                        self._integrate((contraction,))

            # If we did not find any new primes, we have nothing left to try
            if set(sorted_prime_reductibles) == self.prime_reductibles:
                break

    def fill_in_gaps(self) -> None:
        """Add representations for combinations of sinks and generator chars that haven't been established."""
        # As long as we can find an element whose image we haven't fully discovered, we have gaps to fill
        while (
            sink_and_g := self._determine_first_element_with_incomplete_image()
        ) is not None:
            # So we integrate the missing link
            sink, g = sink_and_g
            self._integrate((sink + g,))

    def is_complete(self) -> bool:
        """True if there are no more combinations of sinks and generator chars that haven't been established.

        Returns
        -------
        bool
            ...
        """
        # If there is no element whose image we haven't fully discovered, we are complete
        return self._determine_first_element_with_incomplete_image() is None

    def __call__(self, *reps: str) -> None:
        """Integrates `reps`, and prints the most reduced representation for it, and the group itself."""
        expanded_reps = [expand_notation(rep) for rep in reps]
        most_reduced = self._integrate(expanded_reps)
        print(f"Most reduced: {compress_notation(most_reduced)}")
        print(self)


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
    # Create a set to keep track of all equivalent representation we'll encounter,
    # including the ones in `reps`. If this function is called recursively, `all_equivalent_reps`
    # already exists, and contains already established representations.
    if all_equivalent_reps is None:
        all_equivalent_reps = set()

    for rep in reps:
        # If we have already enouctered `rep`, we don't have to search from it again
        if rep in all_equivalent_reps:
            continue

        # Otherwise we add it now
        all_equivalent_reps.add(rep)

        # If `rep` already has an associated sink, all representations we might reach through reduction
        # are ones for which we've definitely already established equivalence to this sink.
        # We can just add the sink to `all_equivalent_reps`, because since it is a sink,
        # there's no point in trying to reduce it later
        if rep in reps_to_sinks:
            all_equivalent_reps.add(reps_to_sinks[rep])
            continue

        # Otherwise we try to recude `rep` with `prime_reductibles`, and for every prime reductible,
        # we will recursively call this function with the results of the reduction as the new `reps`
        for left in prime_reductibles:
            right = reps_to_sinks[left]

            # Apply the reduction rule `left` -> `right` to `rep`,
            # which could give us multiple reduced representations
            reps_after_application = apply_rule_once(left, right, rep)

            # Recursive call with `reps_after_application` as the new `reps`.
            # `reps_after_application` might be empty, but this is not an issue.
            # Worst case we'll loop over an empty set
            find_all_reachable_representations(
                reps_after_application,
                reps_to_sinks,
                prime_reductibles,
                all_equivalent_reps,
            )

    # Finally we return all reduced representations, including those from deeper levels of recursion
    return all_equivalent_reps
