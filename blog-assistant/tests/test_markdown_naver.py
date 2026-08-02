from __future__ import annotations

from src.markdown_naver import convert, replace_slots


def test_title_is_taken_from_first_h1():
    result = convert("# 포르투 리스본 기차 예약 방법\n\n본문 첫 줄\n")
    assert result.title == "포르투 리스본 기차 예약 방법"
    assert '<h1 style="font-size:1.2em;font-weight:bold;text-align:center;">' in result.body_html


def test_each_line_becomes_its_own_centered_paragraph():
    result = convert("첫 줄\n\n둘째 줄\n")
    assert result.body_html.count('<p style="text-align:center;">') == 2


def test_highlight_bold_strike_and_code():
    result = convert("출발 ==13:40== / **AP 기차** / ~~취소~~ / `코드`\n")
    assert 'background-color:#FFE400;">13:40</span>' in result.body_html
    assert '<strong style="font-weight:bold;">AP 기차</strong>' in result.body_html
    assert "<del>취소</del>" in result.body_html
    assert "<code" in result.body_html and "코드" in result.body_html


def test_blockquote_becomes_bold_paragraph():
    result = convert("> AP 기차가 KTX 같은 개념이에요\n")
    assert "<strong" in result.body_html
    assert "border-left" not in result.body_html


def test_horizontal_rule_and_blank_lines():
    result = convert("위\n\n---\n\n아래\n")
    assert "<hr />" in result.body_html


def test_html_in_source_is_escaped():
    result = convert("<script>alert(1)</script>\n")
    assert "<script>" not in result.body_html
    assert "&lt;script&gt;" in result.body_html


def test_markers_inside_code_span_are_literal():
    result = convert("`**not bold**`\n")
    assert "<strong" not in result.body_html
    assert "**not bold**" in result.body_html


def test_image_markers_become_indexed_slots():
    result = convert(
        "# 제목\n\n도입\n\n[이미지: a.jpg | 기차역 플랫폼]\n\n본문\n\n[이미지: 숙소 내부]\n"
    )
    assert result.slot_bodies == ["a.jpg | 기차역 플랫폼", "숙소 내부"]
    filled = replace_slots(result.body_html, lambda i: f"<!--{i}-->")
    assert "<!--0-->" in filled and "<!--1-->" in filled
