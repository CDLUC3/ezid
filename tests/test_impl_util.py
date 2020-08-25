import pytest

import impl.util


class TestImplUtil:
    """Test the impl.util module."""

    @pytest.mark.parametrize(
        ("sping_str,doi_str"),
        (
            ("c3022/m3", "10.13022/M3"),
            ("c5140/d3", "10.15140/D3"),
            ("c5141/s5", "10.15141/S5"),
            ("c5779/z38", "10.15779/Z38"),
            ("b5070/lx2", "10.5070/LX2"),
            ("b5070/q2", "10.5070/Q2"),
            ("b5070/sb2", "10.5070/SB2"),
            ("d1986/s6.caida", "10.21986/S6.CAIDA"),
        ),
    )
    def test_1000(self, sping_str, doi_str):
        """shadow2doi() successful
        b5060/foo') == '10.5060/FOO
        """
        assert impl.util.shadow2doi(sping_str) == doi_str

    @pytest.mark.parametrize(
        "sping_str",
        (
            # Invalid beta char ("a")
            "a3022/m3",
            # Missing "/"
            "b3022m3",
            # Invalid beta char and missing slash
            "a3022m3",
        ),
    )
    def test_1010(self, sping_str):
        """shadow2doi() invalid
        """
        with pytest.raises(AssertionError) as e:
            impl.util.shadow2doi(sping_str)
        assert e.match("Invalid scheme-less")

    @pytest.mark.parametrize(
        ("doi_str,sping_str"),
        (
            ("10.13022/M3", "c3022/m3"),
            ("10.15140/D3", "c5140/d3"),
            ("10.15141/S5", "c5141/s5"),
            ("10.15779/Z38", "c5779/z38"),
            ("10.5070/LX2", "b5070/lx2"),
            ("10.5070/Q2", "b5070/q2"),
            ("10.5070/SB2", "b5070/sb2"),
            ("10.21986/S6.CAIDA", "d1986/s6.caida"),
        ),
    )
    def test_1020(self, doi_str, sping_str):
        """doi2shadow()"""
        assert impl.util.doi2shadow(doi_str) == sping_str
