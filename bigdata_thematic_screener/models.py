from pydantic import BaseModel, RootModel


class ThemeTaxonomy(BaseModel):
    label: str
    node: int
    summary: str | None
    children: list["ThemeTaxonomy"] = []
    keywords: list[str] | None = None


class LabeledChunk(BaseModel):
    time_period: str
    date: str
    company: str
    sector: str
    industry: str
    country: str
    ticker: str
    document_id: str
    headline: str
    quote: str
    motivation: str
    theme: str


class LabeledContent(RootModel):
    root: list[LabeledChunk] = []


class ThemeScore(RootModel):
    root: dict[str, int]


class CompanyScoring(BaseModel):
    ticker: str | None
    industry: str
    motivation: str | None
    composite_score: int
    themes: ThemeScore


class ThemeScoring(RootModel):
    root: dict[str, CompanyScoring]


class ThematicScreenerResponse(BaseModel):
    theme_scoring: ThemeScoring
    theme_taxonomy: ThemeTaxonomy
    content: LabeledContent | None = None
