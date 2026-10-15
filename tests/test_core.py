import pytest
from brain_twin.retrieval import retrieve
from brain_twin.twin import validate_answer

SOURCES = [
    {"id": "running", "title": "半马训练", "text": "半马训练每周跑三次。长距离慢跑安排在周日，受伤时停止训练。"},
    {"id": "coffee", "title": "手冲咖啡", "text": "咖啡冲煮用九十二度热水，粉水比是一比十五。"},
]


def test_chinese_question_finds_correct_source():
    hits = retrieve("半马训练每周跑几次？", SOURCES)
    assert [hit["id"] for hit in hits] == ["running"]
    assert "每周跑三次" in hits[0]["excerpt"]


def test_unrelated_question_has_no_answer_source():
    assert retrieve("木星的卫星有多少颗？", SOURCES) == []


def test_unknown_citation_is_rejected():
    with pytest.raises(ValueError, match="citation"):
        validate_answer({"status": "answered", "answer": "Three", "citations": [{"source_id": "invented", "quote": "Three"}]}, SOURCES)


def test_quote_must_appear_in_the_retrieved_source():
    with pytest.raises(ValueError, match="quote"):
        validate_answer({"status": "answered", "answer": "Five", "citations": [{"source_id": "running", "quote": "每周跑五次"}]}, SOURCES)


def test_real_quote_cannot_be_attributed_to_another_real_source():
    with pytest.raises(ValueError,match='quote'):
        validate_answer({'status':'answered','answer':'每周跑三次','citations':[{'source_id':'coffee','quote':'半马训练每周跑三次。'}]},SOURCES)
