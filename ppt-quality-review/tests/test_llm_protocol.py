"""VisionReviewer protocol conformance."""

from ppt_quality_review.llm import VisionReviewer


def test_ppt_common_llm_client_satisfies_protocol():
    # LLMClient is lazy-initialised: construction needs no API key.
    from ppt_common.llm import LLMClient

    assert isinstance(LLMClient(), VisionReviewer)


def test_custom_client_satisfies_protocol():
    class MyReviewer:
        def chat_with_images(self, user_prompt, image_paths, *, model=""):
            return '{"passed": true}'

    assert isinstance(MyReviewer(), VisionReviewer)


def test_missing_method_fails_protocol():
    class NotAReviewer:
        pass

    assert not isinstance(NotAReviewer(), VisionReviewer)


def test_llm_client_signature_matches_protocol():
    import inspect

    from ppt_common.llm import LLMClient

    from ppt_quality_review.llm import VisionReviewer

    impl = inspect.signature(LLMClient.chat_with_images)
    proto = inspect.signature(VisionReviewer.chat_with_images)
    impl_params = [
        p.name
        for p in impl.parameters.values()
        if p.kind is p.POSITIONAL_OR_KEYWORD and p.name != "self"
    ]
    proto_params = [
        p.name
        for p in proto.parameters.values()
        if p.kind is p.POSITIONAL_OR_KEYWORD and p.name != "self"
    ]
    assert impl_params[0] == proto_params[0]  # first arg name must match
    assert impl_params[1] == proto_params[1] == "image_paths"
    assert impl.parameters["model"].kind is inspect.Parameter.KEYWORD_ONLY
    assert impl.parameters["model"].default == ""
