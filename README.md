# Group Theory Sandbox

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python-based tool to represent the structure of finite groups, i.e. sets with some operation, satisfying a handful of axioms. This project provides a nice way to explore groups, implementing an algorithm I designed to infer the full structure of a group based on some initial conditions.

---

## Description

Group theory is a foundational concept in mathematics. As it is part of abstract algebra, it is arguably pretty abstract, but it is super fundamental and highly applicable to all sorts of real-life objects. I haven't found a Python package that infers group structure based on some initial information, or at least not one that I found very accessible. I mainly created this because I want to use it to generate music at some point in the future.

If you're new to group theory, there's a lot of great resources available, but by far my favourite is the [All Angles video series](https://youtube.com/playlist?list=PLffJUy1BnWj1vIbqT14uI1bJcoQV3smfo). Personally I learned all I know about group theory from YouTube videos, and probably some Wikipedia pages.

---

## Features

To infer the structure of a group, we can consider equivalences between different string representations of its elements. Check the [showcase notebook](showcase.ipynb) for a demonstration. The algorithm works as follows:

- We keep track of the representations we've encountered in `self.reps_to_sinks`. This is a dict in which the encountered representations refer to the most reduced equivalent representation, as far as we've discovered. (These most reduced representations are called sinks within this project.)
- We can then use the equivalence information in `self.reps_to_sinks` to try and figure out the rest of the structure. If we have two string representations s1, s2 that we can rewrite, and we can somehow combine them in a way that they overlap, we can reduce this contraction in two ways, leading to representations that must be equivalent, which maybe we hadn't discovered yet.
- When we've tried all combinations, we can see whether for all combinations of sinks and generator characters, we have a representation of their composition in `self.reps_to_sinks`.
- If so, we know we have discovered the full group structure. If not, we can integrate these combinations until everything is linked up.

### In All Honesty
I have not devised a formal proof that this always leads to the discovery of the full structure, but I'm pretty sure it does. ✌️ There are probably other algorithms out there that are more rigorous, albeit just in terms of acknowledgements of limitations, but I thought it would be a good exercise to figure this out myself.

### Glossary
Below is a glossary of some of the terminology used in this implementation, some of which I came up with, and because I'm not schooled in abstract algebra, there are probably other terms out there for some of the concepts I'm using, but some of them are also specific to the way I chose to represent things:
- **Representation**: A representation (rep) is a string that represents a group element. By the axiom of closure, we know that all reps that only contain generator characters also represent some element in the group.
- **Generator character**: A rep of length 1. All other reps can be thought of as compositions of generator characters.
- **Equivalent representations**: Two reps `s1` and `s2` are equivalent if they describe the same group element. For example, in the **integers mod 4**, 4 and 0 are equivalent. If we use `"R"` to represent the number 1 (mod 4), we can say that `"RRRR"` and `""` are equivalent representations for this group.
- **Identity element**: Every group contains an identity element, which, when composed with any other element `element`, results in `element`, leaving it unchanged. The identity element is often denoted as `"e"`. This program will interpret `"e"` to be the identity, but internally it is represented by the empty string.
- **Sink**: A representation of which we don't know how to reduce it any further. This can mean that it's the most reduced representation that the structure of the group allows, or that we have yet to discover a way to recude it. So at some point during the process, we can have two strings that both represent the same group element, and yet they are both considered sinks. Sinks are kept track of in `self.sinks`, and they are represented in `self.reps_to_sinks` as strings refering to themselves.
- **Reductible representation**: A representation that is not a sink. We can use a reductible representation to reduce other representations. For example if we have exactly one entry in `self.reps_to_sinks`, such that `self.reps_to_sinks["HH"] := "e"`, we can use this to reduce `"HHH"` to `"H"`, because `"HHH"` contains `"HH"`. Of course we could do this in two different ways, rewriting the left-most pair or the right-most pair, but in this case this will lead to the same outcome.
- **Prime reductible**: A representation `rep` that is reductible, and is associated with a sink `sink`, such that we could not reach `sink` if we tried to reduce `rep` using already established prime reductibles. In the above example, `"HH"` is a prime reductible, but `"HHH"` isn't. `"HHH"` could be called a redundant reductible.
- **Combined prime reductibles**: (or contractions of prime reductibles): If we know we can recude `"rH"` to `"Hr"`, and `"rrr"` to `""` (identity), we can contract `"rH"` and `"rrr"` to `"rrrH"`, such that one `"r"` overlaps. This representation can be reduced both to `"rrHr"` and to `"H"`, giving us two equivalent representations whose equivalence we might not have been aware of yet.
- **Inverse element**: One of the group axioms asserts that every element has an inverse element. For generator characters, the inverse is represented by the same letter, but with the opposite case. The inverse of the element `"R"` is thus represented by `"r"`, such that `"Rr"` is equivalent to `"rR"`, and they both represent the identity element. The inverse of `"abc"` is `"CBA"`, but this is not always the most reduced representation available.
- **Shaved (pairs of) representations**: If we figured out `"r"` and `"rHrr"` represent the same element, and we have no way to further reduce either of them through our prime reductibles, we could consider `"rHrr"` a new prime reductible, with sink `"r"`. But because of the axiom of inverses, we can claim that `""` and `"Hrr"` must also be equivalent, and the same goes for `""` and `"rHr"`. This is what I decided to call shaving, where `"r"` and `"rHrr"` are not a shaved pair, and `""` and `"Hrr"` are. We should use `"Hrr"` as a prime reductible instead, because we can use it to reduce `"rHrr"`, and also other representations that we wouldn't be able to recude if we just used `"rHrr"`.
- **Composition**: Any two group elements can be composed to get a new group element. In terms of representations, this can be thought of as just concatenating two representations.
- **Image**: The image of some element represented by `s1` can be thought of as a mapping, such that the rep `s2` will be mapped to the composition of `s1` and `s2`. We can check that we have discovered the full group structure if we have defined the image over the generator characters for all sinks. I hope this sentence makes sense at this point. Also hey! How come you are reading all of this text? I just put this online as a hobby project for my portfolio but I didn't think somebody would read the full glossary, that's a bit weird tbh, I think you're a bit weird for that.

---

## Usage

For an overview of how to use this code, I would refer you to the [showcase notebook](notebooks/showcase.ipynb)

---

## Tests

Unit tests are provided to ensure correctness, and you can find them in the [tests folder](tests/). To run them, use the `unittest` package.

---

## Future Plans

This project is a work-in-progress, and future updates may include:
- Additional methods for analysing and visualising group properties, such as checking isomorphism to other groups, generating Cayley graphs.
- Implementing new classes that use the Group class, such as the class `Combination`. This class will be able to represent a set containing some elements of some group, that we can use to represent musical chords and scales for example. We can use the cyclic group C12 for this, but it would be interesting to use different groups instead and see what that sounds like.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
