from app.core.stem_norm import stem_fingerprint


def test_stem_fingerprint_collapses_space_and_case() -> None:
    assert stem_fingerprint("  A  B  ") == stem_fingerprint("a b")
    assert stem_fingerprint("Hello World") == "helloworld"
