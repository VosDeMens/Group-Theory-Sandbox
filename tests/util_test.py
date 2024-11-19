import unittest

import src.util as util


class UtilTests(unittest.TestCase):
    def test_expand_notation(self):
        # create
        HH = util.expand_notation(s="H2")
        empty = util.expand_notation(s="e")
        Hr = util.expand_notation(s="Hr")
        rrH = util.expand_notation(s="rrH")
        rrrrHrr = util.expand_notation("r4Hrr")

        # check
        self.assertEqual(HH, "HH")
        self.assertEqual(empty, "")
        self.assertEqual(Hr, "Hr")
        self.assertEqual(rrH, "rrH")
        self.assertEqual(rrrrHrr, "rrrrHrr")

    def test_get_most_shaved(self):
        # create
        HH_empty = util.get_most_shaveds(s1="HH", s2="")
        HH_empty2 = util.get_most_shaveds(s1="HHH", s2="H")
        Hrr_empty_rrH_empty = util.get_most_shaveds(s1="rrHrr", s2="rr")
        Hr_empty_rH_empty = util.get_most_shaveds(s1="rrHr", s2="rr")
        H_empty = util.get_most_shaveds(s1="rrHr", s2="rrr")

        # check
        self.assertEqual(HH_empty, {("HH", "")})
        self.assertEqual(HH_empty2, {("HH", "")})
        self.assertEqual(Hrr_empty_rrH_empty, {("Hrr", ""), ("rrH", "")})
        self.assertEqual(Hr_empty_rH_empty, {("Hr", ""), ("rH", "")})
        self.assertEqual(H_empty, {("H", "")})

    def test_apply_rule_once(self):
        # create
        ba_ab = util.apply_rule_once("aa", "b", "aaa")
        cab = util.apply_rule_once("aba", "c", "abaab")
        ababcba_abcbaba = util.apply_rule_once("bc", "", "abcbabcba")
        empty = util.apply_rule_once(unreduced="HH", reduced="", s="Hr")
        empty2 = util.apply_rule_once(unreduced="HH", reduced="", s="rrH")

        # check
        self.assertCountEqual(ba_ab, ["ba", "ab"])
        self.assertCountEqual(cab, ["cab"])
        self.assertCountEqual(ababcba_abcbaba, ["ababcba", "abcbaba"])
        self.assertCountEqual(empty, [])
        self.assertCountEqual(empty2, [])

    def test_compress_notation(self):
        # create
        e = util.compress_notation("")
        r = util.compress_notation("r")
        r2 = util.compress_notation("rr")
        r3 = util.compress_notation("rrr")
        rR = util.compress_notation("rR")
        Rr2 = util.compress_notation("Rr2")
        R2r2 = util.compress_notation("R2r2")
        g2l = util.compress_notation("ggl")
        Hr = util.compress_notation(s="Hr")
        H2 = util.compress_notation(s="HH")
        r2H = util.compress_notation(s="rrH")

        # check
        self.assertEqual(e, "e")
        self.assertEqual(r, "r")
        self.assertEqual(r2, "r2")
        self.assertEqual(r3, "r3")
        self.assertEqual(rR, "rR")
        self.assertEqual(Rr2, "Rr2")
        self.assertEqual(R2r2, "R2r2")
        self.assertEqual(g2l, "g2l")
        self.assertEqual(Hr, "Hr")
        self.assertEqual(H2, "H2")
        self.assertEqual(r2H, "r2H")


if __name__ == "__main__":
    unittest.main()
