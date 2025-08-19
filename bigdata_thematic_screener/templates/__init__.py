from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bigdata_thematic_screener.settings import settings

loader = Environment(loader=FileSystemLoader(searchpath=Path(settings.TEMPLATES_DIR)))
