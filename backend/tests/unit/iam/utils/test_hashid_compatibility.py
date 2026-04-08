from src.apps.iam.utils.hashid import decode_id, decode_id_or_404, encode_id


def test_decode_id_supports_documented_numeric_backward_compatibility() -> None:
    assert decode_id(42) == 42
    assert decode_id("42") == 42


def test_decode_id_supports_canonical_hashid_inputs() -> None:
    encoded = encode_id(1234)
    assert decode_id(encoded) == 1234


def test_decode_id_or_404_accepts_hashid_and_numeric_inputs() -> None:
    encoded = encode_id(77)
    assert decode_id_or_404(encoded) == 77
    assert decode_id_or_404("77") == 77
