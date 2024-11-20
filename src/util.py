from functools import lru_cache
import re


@lru_cache(maxsize=None)
def generate_contractions(s1: str, s2: str) -> set[str]:
    """Generates all possible overlaps between two strings.

    Parameters
    ----------
    s1 : str
        First string.
    s2 : str
        Second string.

    Returns
    -------
    set[str]
        All possible overlaps.

    Examples
    --------
    >>> s1 = "Hrr"
    >>> s2 = "rrH"
    >>> generate_contractions(s1, s2)
    {'HrrH', 'rrHrr', 'HrrrH'}
    """
    max_len: int = min(len(s1), len(s2))
    contractions: set[str] = set()

    # Check for equality for all sizes `overlap`, both ways around
    for overlap in range(max_len):
        end_of_s1: str = s1[-overlap:]
        start_of_s2: str = s2[:overlap]

        if end_of_s1 == start_of_s2:
            contraction: str = s1 + s2[overlap:]
            contractions.add(contraction)

        end_of_s2: str = s2[-overlap:]
        start_of_s1: str = s1[:overlap]
        if end_of_s2 == start_of_s1:
            contraction: str = s2 + s1[overlap:]
            contractions.add(contraction)

    return contractions


@lru_cache(maxsize=None)
def apply_rule_once(unreduced: str, reduced: str, s: str) -> set[str]:
    """Returns all representations we can reach by applying `rule` once to `s`.

    Any occurence of `unreduced` within `s` will lead to one element in the returned list.
    The returned strings may still be reducible further.

    Parameters
    ----------
    unreduced : str
        The substring to be replaced.
    reduced : str
        The replacing substring.
    s : str
        The string to be reduced.

    Returns
    -------
    set[str]
        The possible reductions.

    Examples
    --------
    >>> unreduced = "HH"
    >>> reduced = ""
    >>> s = "HHrHH"
    >>> print(apply_rule_once(unreduced, reduced, s))
    {"HHr", "rHH"}
    """
    results: set[str] = set()
    start = 0
    while (index := s.find(unreduced, start)) != -1:
        new_string = s[:index] + reduced + s[index + len(unreduced) :]
        results.add(new_string)
        start = index + 1
    return results


@lru_cache(maxsize=None)
def get_most_shaveds(s1: str, s2: str) -> set[tuple[str, str]]:
    """Returns `s1` and `s2`, but without any characters that `s1` and `s2` both end or both start with.

    This can lead to different outcomes depending on whether you start from left or right,
    but often it doesn't, and then this function is going to return a singleton set.

    Parameters
    ----------
    s1 : str
        First string
    s2 : str
        Second string

    Returns
    -------
    set[tuple[str, str]]
        Set of tuples of shaved strings.

    Examples
    --------
    >>> s1 = "HH"
    >>> s2 = ""
    >>> get_most_shaveds(s1, s2)
    {('HH', '')}

    >>> s1 = "rrHrr"
    >>> s2 = "rr"
    >>> get_most_shaveds(s1, s2)
    {('rrH', ''), ('Hrr', '')}
    """
    # Left first
    limit: int = min(len(s1), len(s2))
    overlap_left: int = 0

    while overlap_left < limit and s1[overlap_left] == s2[overlap_left]:
        overlap_left += 1

    # We don't want the right overlap to overlap the left overlap (makes sense?)
    limit -= overlap_left
    overlap_right: int = 0
    while overlap_right < limit and s1[-overlap_right - 1] == s2[-overlap_right - 1]:
        overlap_right += 1

    most_shaved_left_first = (
        s1[overlap_left : len(s1) - overlap_right],
        s2[overlap_left : len(s2) - overlap_right],
    )

    # If both of the shaved representations are non-empty, we will find the same results
    # if we start from the other side, so we can just return the result now
    if len(most_shaved_left_first) > 0 and len(most_shaved_left_first[1]) > 0:
        return {most_shaved_left_first}

    # Otherwise we do the same starting from the right. Of course we need to reset `limit` to 0
    limit: int = min(len(s1), len(s2))
    overlap_right: int = 0
    while overlap_right < limit and s1[-overlap_right - 1] == s2[-overlap_right - 1]:
        overlap_right += 1

    limit -= overlap_right
    overlap_left: int = 0
    while overlap_left < limit and s1[overlap_left] == s2[overlap_left]:
        overlap_left += 1

    most_shaved_right_first = (
        s1[overlap_left : len(s1) - overlap_right],
        s2[overlap_left : len(s2) - overlap_right],
    )

    return {most_shaved_left_first, most_shaved_right_first}


@lru_cache(maxsize=None)
def expand_notation(s: str) -> str:
    """Turns a human readable representation into a computer readable one.

    A human readable representation can contain numbers representing powers.
    Also any "e"'s are removed, as they represent the identity element.
    See examples.

    Parameters
    ----------
    s : str
        String to expand.

    Returns
    -------
    str
        Expanded string.

    Raises
    ------
    SyntaxError
        If `s` contains an uppercase "E", we raise a `SyntaxError`, because we would need "e"
        to represent its inverse, but "e" is reserved for the identity element.
    SyntaxError
        If after expansion, the representation still contains non-alphabetic characters,
        we also raise a `SyntaxError`

    Examples
    --------
    >>> s = "H2r3"
    >>> print(expand_notation(s))
    HHrrr

    >>> s = "r5eH"
    >>> print(expand_notation(s))
    rrrrrH
    """
    if "E" in s:
        raise SyntaxError(
            f'{s = } should not contain the letter "E", because we would need "e" to represent its inverse, but "e" is reserved for the identity element'
        )

    # Replace all occurences of "e", representing the identity element, with the empty string
    s = s.replace("e", "")

    # H4r2 -> HHHHrr
    expanded = re.sub(r"([a-zA-Z])(\d+)", lambda m: m.group(1) * int(m.group(2)), s)

    if expanded and not expanded.isalpha():
        raise SyntaxError(
            f"{s = } is invalid. After expansion, {expanded = } is not alphabetic"
        )

    return expanded


@lru_cache(maxsize=None)
def compress_notation(s: str) -> str:
    """Turns a computer readable representation into a human readable one.

    See `expand_notation` or examples.

    Parameters
    ----------
    s : str
        String to compress.

    Returns
    -------
    str
        Compressed string.

    Examples
    --------
    >>> s = ""
    >>> print(compress_notation(s))
    e

    >>> s = "HHrrrrH"
    >>> print(compress_notation(s))
    H2r4H
    """
    # "e" represents the identity element
    if s == "":
        return "e"

    # HHHHrr -> H4r2
    compressed = re.sub(
        r"([a-zA-Z])\1+", lambda m: f"{m.group(0)[0]}{len(m.group(0))}", s
    )
    return compressed


@lru_cache(maxsize=None)
def anti_cap(s: str) -> str:
    """Returns `s` with inverted case.

    Parameters
    ----------
    s : str
        A single character, of which to invert the case

    Returns
    -------
    str
        The character with inverted case

    Examples
    --------
    >>> anti_cap("r")
    'R'
    >>> anti_cap("R")
    'r'
    """
    assert len(s) == 1, "expecting single character"
    if s.islower():
        return s.capitalize()
    return s.lower()


@lru_cache
def get_inverse_rep(s: str) -> str:
    """Reverses `s` and makes all characters the opposite case.

    Parameters
    ----------
    s : str
        Rep to invert.

    Returns
    -------
    str
        Inverse.
    """
    s_expanded = expand_notation(s)
    return "".join(anti_cap(c) for c in reversed(s_expanded))
