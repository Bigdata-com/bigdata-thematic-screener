import pandas as pd
import pytest

from bigdata_thematic_screener.models import (
    LabeledContent,
    ThematicScreenerResponse,
    ThemeScoring,
    ThemeTaxonomy,
)
from bigdata_thematic_screener.service import ThemeTree, build_response


@pytest.fixture
def df_company():
    return pd.DataFrame(
        [
            {
                "Company": "A",
                "Ticker": "T1",
                "Sector": "S1",
                "Industry": "I1",
                "Composite Score": 55,
                "Theme1": 55,
            },
            {
                "Company": "B",
                "Ticker": "T2",
                "Sector": "S2",
                "Industry": "I2",
                "Composite Score": 50,
                "Theme1": 45,
                "Theme 2 with long name": 5,
            },
        ]
    )


@pytest.fixture
def df_motivation():
    return pd.DataFrame(
        [
            {
                "Company": "A",
                "Motivation": "Growth",
            },
            {
                "Company": "B",
                "Motivation": "Decline",
            },
        ]
    )


@pytest.fixture
def df_labeled():
    return pd.DataFrame(
        [
            {
                "Time Period": "2025Q1",
                "Date": "2025-01-01",
                "Company": "A",
                "Sector": "S1",
                "Industry": "I1",
                "Country": "US",
                "Ticker": "T1",
                "Document ID": "D1",
                "Headline": "Headline1",
                "Quote": "Quote1",
                "Motivation": "Growth",
                "Theme": "Theme1",
            },
            {
                "Time Period": "2025Q1",
                "Date": "2025-01-02",
                "Company": "B",
                "Sector": "S2",
                "Industry": "I2",
                "Country": "UK",
                "Ticker": "T2",
                "Document ID": "D2",
                "Headline": "Headline2",
                "Quote": "Quote2",
                "Motivation": "Decline",
                "Theme": "Theme2",
            },
        ]
    )


@pytest.fixture
def theme_tree():
    return ThemeTree(
        label="Root",
        node=1,
        summary="Root node",
        children=[
            ThemeTree(label="Theme1", node=2, summary="Theme1 for company"),
            ThemeTree(
                label="Theme 2 with long name", node=3, summary="Theme 2 for company"
            ),
        ],
    )


def test_build_response(df_company, df_labeled, df_motivation, theme_tree):
    response = build_response(df_company, df_motivation, df_labeled, theme_tree)
    assert isinstance(response, ThematicScreenerResponse)
    assert isinstance(response.theme_taxonomy, ThemeTaxonomy)
    assert isinstance(response.theme_scoring, ThemeScoring)
    assert isinstance(response.content, LabeledContent)
    assert len(response.content.root) == 2
