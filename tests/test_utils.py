from tools.build_xml_corpus import slugify


def test_slugify_basic():
    assert slugify("Paper One v2") == "paper-one-v2"
