"""Theme taxonomy generation, leaf-node helpers, and labeling/summary prompts.

Ported from ``Thematic_Screener_CLI/src/screener.py`` (thematic-screener mode),
``src/prompts.py`` (thematic-mode prompts), ``src/helpers.py``, and
``src/search_query.py``. Replaces
``bigdata_research_tools.tree.SemanticTree`` / ``generate_theme_tree``.
"""

from __future__ import annotations

import re

from openai import OpenAI
from pydantic import BaseModel, Field

DEFAULT_MAX_LEAF_LABELS = 15

# ---------------------------------------------------------------------------
# Prompts (thematic-screener mode), verbatim from Thematic_Screener_CLI/src/prompts.py
# ---------------------------------------------------------------------------

SYSTEM_MESSAGE_LABELS = """
Forget all previous prompts.
You are assisting a professional analyst building a thematic company screener.
The screener should identify companies that are economically exposed to the theme:
{main_theme}

Analyst focus:
{analyst_focus}

Your objective is to create a generic exposure taxonomy that works for any theme, including
technology adoption, infrastructure buildout, geopolitical conflict, regulation, supply-chain
shocks, M&A/IPO events, commodity cycles, consumer behavior shifts, and policy changes.

Follow these rules strictly:

1. **Classify exposure pathways, not generic topic concepts**
   - Each leaf must describe a distinct way a company can make money, save cost, lose money,
     face operational risk, or gain/lose strategic relevance because of {main_theme}.
   - Prefer value-chain roles over broad nouns. Separate buyers/operators from vendors,
     direct suppliers from component suppliers, materials/construction from software/services,
     owners/financiers from operating companies, and risk-bearers from beneficiaries.
   - Do not create labels that imply the wrong role. For example, a data center operator
     adopting liquid cooling is not a cooling vendor; it is an operator/customer exposed
     through cooling adoption.

2. **Use generic role categories when they fit**
   Consider whether the theme needs leaf labels for:
   - operators/customers adopting or exposed to the theme
   - direct product or service suppliers
   - component, materials, or equipment suppliers
   - infrastructure, construction, logistics, or capacity providers
   - software, data, analytics, cybersecurity, or operational enablement providers
   - asset owners, financiers, insurers, or lessors
   - companies exposed to sanctions, disruption, regulation, litigation, or demand destruction

3. **Keep leaves distinct: analyst fields vs retrieval query**
   - `label`: concise exposure-pathway name for analysts (3-8 words).
   - `summary`: analyst taxonomy phrase, maximum 25 words, describing company role and
     exposure mechanism. May use analyst framing such as "Companies that...".
   - `search_query` (leaf nodes only): document/disclosure voice phrase for semantic search
     against filings, transcripts, and news. Write as if quoting company language:
     "The company [verb] [products/services] [to/for] [customers/market]."
   - Do not copy `summary` verbatim into `search_query`; rewrite into operational language.
   - Avoid exposure-meta phrasing in `search_query` (for example: exposed to, benefiting from,
     profiting from, IPO-driven, capex scaling).
   - Use 5-8 leaf labels unless the analyst focus asks for a different breadth.
   - For narrow themes, fewer precise leaves are better than many weak leaves.

4. **Use the analyst focus**
   - Emphasize exposure pathways that answer the analyst focus.
   - Exclude academic background concepts that do not help classify companies.

5. **Format your response as valid JSON only**
   - Each node must include only these fields: `node`, `label`, `summary`, `search_query`,
     `children`.
   - `node`: an integer identifier.
   - `label`: concise name for the exposure pathway or grouping.
   - `summary`: analyst exposure mechanism, maximum 25 words.
   - `search_query`: required on leaf nodes; use an empty string on branch nodes.
   - `children`: an array of child nodes. Use an empty array for leaf nodes.
   - Return only the JSON object. Do not include markdown or commentary.

Example for theme "Data center development":
{{
  "node": 1,
  "label": "Data center development exposure",
  "summary": "Company exposure to data center construction, operation, supply, or financing.",
  "search_query": "",
  "children": [
    {{
      "node": 2,
      "label": "Operators and customers",
      "summary": "Companies operating or expanding cloud, AI, colocation, or telecom data centers.",
      "search_query": "The company operates or expands cloud, colocation, or telecom data centers.",
      "children": []
    }},
    {{
      "node": 3,
      "label": "Power infrastructure suppliers",
      "summary": "Companies supplying UPS, generators, switchgear, transformers, or power systems.",
      "search_query": "The company supplies UPS, generators, switchgear, or power systems to data centers.",
      "children": []
    }},
    {{
      "node": 4,
      "label": "Cooling and thermal management suppliers",
      "summary": "Companies selling HVAC, chillers, liquid cooling, or thermal systems.",
      "search_query": "The company sells HVAC, chillers, and liquid cooling systems to data center operators.",
      "children": []
    }}
  ]
}}"""

USER_MESSAGE_LABELS = "Your given Theme is: {main_theme}"

SYSTEM_PROMPT_LABELING = """Forget all previous prompts.
You are assisting a professional analyst with a thematic company screener.

Theme:
{main_theme}

Analyst focus (mandatory scope):
{analyst_focus}

Exposure labels:
{labels}

Your task is to decide whether each input sentence provides evidence that the target company
has economic exposure to the theme within the analyst focus scope, then assign the best matching
exposure label.

Guidelines:

1. **Classify economic exposure within analyst focus scope**
   - A sentence is relevant only if it connects the target company to a business activity,
     product, service, customer demand, supply chain, asset, cost, risk, or strategic action
     related to the theme.
   - The analyst focus defines mandatory scope constraints such as geography, counterparties,
     event type, customer segment, or time window. Apply these constraints as strictly as the
     exposure mechanism.
   - Assign a label only when the sentence supports both the exposure mechanism and the analyst
     focus scope. If the mechanism matches a label but the scope does not, assign `unclear`.
   - Do not treat label names, theme wording, or structurally similar exposures in other
     geographies or contexts as sufficient when the analyst focus narrows scope.
   - When the analyst focus does not narrow scope, the exact theme words do not need to appear
     if the exposure mechanism is explicit.
   - Assign `unclear` when the sentence merely mentions the topic, a peer, a market backdrop,
     or a customer trend without connecting it to the target company's exposure.

2. **Respect company role**
   - Choose the label that matches the company's role in the value chain.
   - Separate demand-side exposure from supply-side exposure.
   - Do not classify an operator/customer as a vendor just because it buys or adopts a product.
   - Do not classify a supplier as an operator/customer just because its customers operate in
     the theme.
   - If the sentence supports exposure but the available labels all imply the wrong role,
     assign `unclear`.

3. **Use only the provided labels**
   - Select exactly one label from the provided labels, or `unclear`.
   - Do not invent a new label.
   - Prefer the most specific label supported by the sentence.

4. **Evidence standard**
   - Use only the sentence content and the provided company name.
   - The sentence must support the label directly enough that an analyst could cite it.
   - If the sentence is ambiguous, promotional without a clear company role, or only about a
     different company, assign `unclear`.

5. **Revenue and cost fields**
   - `revenue_generation`: `high`, `medium`, `low`, or `Nan` depending on whether the sentence
     indicates the target company can generate revenue from the exposure.
   - `cost_efficiency`: `high`, `medium`, `low`, or `Nan` depending on whether the sentence
     indicates the target company can reduce costs or improve efficiency from the exposure.

6. **Materiality field**
   - `materiality`: `high`, `medium`, `low`, or `unclear`.
   - Use `high` for direct revenue, cost, valuation, capex, supply-chain, regulatory, or
     operational impact on a major business line, asset, contract, ownership stake, or risk.
   - Use `medium` for clear exposure through a relevant product, market, customer, supplier,
     competitor, financing, or operating role, but without strong magnitude evidence.
   - Use `low` for indirect exposure, customer/adopter exposure, weak proxy exposure, market
     sentiment, or relevant but likely non-core business impact.
   - Use `unclear` when the label is `unclear`.

7. **Response format**
   - Return valid JSON only.
   - Format your JSON as:
     {{"<sentence_id>": {{"motivation": "<motivation>", "label": "<label>",
     "revenue_generation": "<revenue_generation>", "cost_efficiency": "<cost_efficiency>",
     "materiality": "<materiality>"}}}}
   - The motivation must begin with "Target Company" and explain the company role, the exposure
     mechanism, how the sentence satisfies the analyst focus scope, materiality level, and why
     the selected label is better than other label roles.
   - Ensure all strings are correctly quoted."""

THEMATIC_SUMMARY_TEMPLATE = """You are assisting a professional analyst evaluating how the theme
"{main_theme}" affects companies.

You will receive a company name and a list of analyst motivations. Each motivation explains why a
specific sentence was labeled in the context of the theme.

Write one cohesive company-level summary that:
- Synthesizes the main themes and business exposures implied by the motivations
- Highlights the most important products, markets, and revenue/cost drivers when mentioned
- Avoids repeating the same point; merge overlapping motivations
- Uses clear, professional prose (1 short paragraph)
- Does not invent facts beyond what the motivations support

Return JSON only: {{"summary": "<your summary>"}}"""


# ---------------------------------------------------------------------------
# Taxonomy tree
# ---------------------------------------------------------------------------


class Node(BaseModel):
    """Recursive node of the theme taxonomy returned by the LLM."""

    node: int
    label: str
    summary: str
    search_query: str = ""
    children: list[Node] = Field(default_factory=list)


Node.model_rebuild()


def normalize_max_leaf_labels(max_leaf_labels: int | None) -> int | None:
    """Return ``None`` when ``max_leaf_labels`` is unset or ``0`` (no cap)."""
    if max_leaf_labels is None or max_leaf_labels == 0:
        return None
    if max_leaf_labels < 0:
        raise ValueError("max_leaf_labels must be zero or positive")
    return max_leaf_labels


def analyst_focus_with_leaf_cap(analyst_focus: str, max_leaf_labels: int | None) -> str:
    """Append a leaf-count instruction for taxonomy generation when capped."""
    cap = normalize_max_leaf_labels(max_leaf_labels)
    if cap is None:
        return analyst_focus
    return f"{analyst_focus}\nLimit the final tree to at most {cap} leaf nodes."


def analyst_focus_with_keywords(analyst_focus: str, keywords: list[str] | None) -> str:
    """Append optional analyst keywords to the focus text used for taxonomy generation."""
    if not keywords:
        return analyst_focus
    return f"{analyst_focus}\nEmphasize these key terms: {', '.join(keywords)}."


def analyst_focus_with_depth_cap(analyst_focus: str, max_depth: int | None) -> str:
    """Append a tree-depth instruction for taxonomy generation when capped.

    ``max_depth`` counts levels including the root theme node. This is a soft
    hint only — :func:`truncate_depth` is the hard guarantee applied after
    generation, since models don't reliably follow depth instructions.
    """
    if max_depth is None:
        return analyst_focus
    return (
        f"{analyst_focus}\nIMPORTANT structural override: build the tree with at most "
        f"{max_depth} levels total, counting the root theme node as level 1. Leaf "
        f"exposure-pathway nodes must not be deeper than level {max_depth}."
    )


def truncate_depth(node: Node, max_depth: int | None, _current_depth: int = 1) -> Node:
    """Return a copy of ``node`` with any branch deeper than ``max_depth`` cut off.

    A node at ``_current_depth == max_depth`` is turned into a leaf (its
    children are dropped), regardless of what the LLM actually returned. The
    root node is depth 1. No-op when ``max_depth`` is ``None``.
    """
    if max_depth is None or not node.children:
        return node
    if _current_depth >= max_depth:
        return node.model_copy(update={"children": []})
    return node.model_copy(
        update={
            "children": [
                truncate_depth(child, max_depth, _current_depth + 1)
                for child in node.children
            ]
        }
    )


def generate_taxonomy(
    main_theme: str,
    analyst_focus: str,
    model: str,
    client: OpenAI | None = None,
    max_leaf_labels: int | None = DEFAULT_MAX_LEAF_LABELS,
    max_depth: int | None = None,
) -> Node:
    """Generate the theme exposure taxonomy tree for ``main_theme`` via the LLM.

    ``max_depth`` (when set) is enforced deterministically via
    :func:`truncate_depth` after generation, on top of a soft prompt hint —
    see :func:`analyst_focus_with_depth_cap`.
    """
    openai_client = client if client is not None else OpenAI()
    focus_for_prompt = analyst_focus_with_leaf_cap(analyst_focus, max_leaf_labels)
    focus_for_prompt = analyst_focus_with_depth_cap(focus_for_prompt, max_depth)
    completion = openai_client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_MESSAGE_LABELS.format(
                    main_theme=main_theme, analyst_focus=focus_for_prompt
                ),
            },
            {
                "role": "user",
                "content": USER_MESSAGE_LABELS.format(main_theme=main_theme),
            },
        ],
    )

    content = completion.choices[0].message.content
    root = Node.model_validate_json(content)
    return truncate_depth(root, max_depth)


# ---------------------------------------------------------------------------
# Leaf-node helpers (ported from src/helpers.py)
# ---------------------------------------------------------------------------

_EXPOSURE_META_PATTERN = re.compile(
    r"\b(exposed to|exposure|ipo-?driven|capex scaling|beneficiar(?:y|ies)|spillover|"
    r"earning returns|profiting from|gain from|benefiting from)\b",
    re.IGNORECASE,
)
_NOMINAL_PREFIX_PATTERN = re.compile(
    r"^(companies|suppliers|vendors|operators|contractors|lenders|prime contractors)\b",
    re.IGNORECASE,
)


def normalize_summary_to_search_query(text: str) -> str:
    """Best-effort rewrite of taxonomy phrasing into document-voice retrieval text."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned

    rewritten = _NOMINAL_PREFIX_PATTERN.sub("The company", cleaned)
    rewritten = _EXPOSURE_META_PATTERN.sub("", rewritten)
    rewritten = re.sub(r"\s{2,}", " ", rewritten).strip(" ,.;")
    if rewritten and not rewritten.endswith("."):
        rewritten = f"{rewritten}."
    return rewritten


def get_leaf_labels(node: Node) -> list[str]:
    """Return leaf ``label`` values in tree order."""
    if not node.children:
        return [node.label]
    labels: list[str] = []
    for child in node.children:
        labels.extend(get_leaf_labels(child))
    return labels


def get_leaf_search_queries(node: Node) -> list[str]:
    """Return leaf search-query text, deriving it from ``summary`` when absent."""
    if not node.children:
        query = (node.search_query or "").strip()
        if query:
            return [query]
        summary = (node.summary or "").strip()
        if summary:
            return [normalize_summary_to_search_query(summary)]
        return [node.label.strip()]

    queries: list[str] = []
    for child in node.children:
        queries.extend(get_leaf_search_queries(child))
    return queries


def build_leaf_ancestry(
    node: Node, ancestors: list[str] | None = None
) -> dict[str, list[str]]:
    """Map each leaf ``label`` to its ancestor labels (root first)."""
    chain = ancestors or []
    if not node.children:
        return {node.label: list(chain)}

    mapping: dict[str, list[str]] = {}
    child_ancestors = [*chain, node.label]
    for child in node.children:
        mapping.update(build_leaf_ancestry(child, child_ancestors))
    return mapping
