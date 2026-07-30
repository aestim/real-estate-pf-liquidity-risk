from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "pf_liquidity_risk" / "v2_app.py"


def test_v2_dashboard_starts_with_beginner_defaults():
    app = AppTest.from_file(str(APP_PATH), default_timeout=15).run()

    assert not app.exception
    assert app.title[0].value == "PF 사업 안전성 계산기"
    assert app.radio[0].value == "기준"
    assert [tab.label for tab in app.tabs] == [
        "한눈에 보기",
        "돈 흐름 자세히",
        "가상 미래 테스트",
    ]
    assert any(metric.label == "은행 대환한도" for metric in app.metric)


def test_v2_dashboard_can_switch_to_conservative_preset():
    app = AppTest.from_file(str(APP_PATH), default_timeout=15).run()

    app.radio[0].set_value("보수적").run()

    assert not app.exception
    assert app.radio[0].value == "보수적"
    assert any("임대는 약하고" in caption.value for caption in app.caption)
    assert any("M42 부실 처리" in markdown.value for markdown in app.markdown)
