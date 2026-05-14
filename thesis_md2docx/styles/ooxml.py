from __future__ import annotations

from xml.sax.saxutils import escape

from ..constants import W_NS
from .catalog import DocumentDefaultsSpec, StyleCatalog, StyleSpec


def _props_xml(tag: str, props: tuple[str, ...]) -> str:
    return f"<w:{tag}>{''.join(props)}</w:{tag}>" if props else ""


def _doc_defaults_xml(defaults: DocumentDefaultsSpec) -> str:
    if defaults.run_props:
        run_defaults = f"<w:rPrDefault><w:rPr>{''.join(defaults.run_props)}</w:rPr></w:rPrDefault>"
    else:
        run_defaults = "<w:rPrDefault/>"
    if defaults.paragraph_props:
        paragraph_defaults = f"<w:pPrDefault><w:pPr>{''.join(defaults.paragraph_props)}</w:pPr></w:pPrDefault>"
    else:
        paragraph_defaults = "<w:pPrDefault/>"
    return f"<w:docDefaults>{run_defaults}{paragraph_defaults}</w:docDefaults>"


def _style_xml(style: StyleSpec) -> str:
    attrs = [f'w:type="{escape(style.style_type)}"']
    if style.default:
        attrs.append('w:default="1"')
    attrs.append(f'w:styleId="{escape(style.style_id)}"')

    parts = [f"<w:style {' '.join(attrs)}>"]
    parts.append(f'<w:name w:val="{escape(style.name)}"/>')
    if style.based_on:
        parts.append(f'<w:basedOn w:val="{escape(style.based_on)}"/>')
    if style.next_style:
        parts.append(f'<w:next w:val="{escape(style.next_style)}"/>')
    if style.q_format:
        parts.append("<w:qFormat/>")
    parts.append(_props_xml("pPr", style.paragraph_props))
    parts.append(_props_xml("rPr", style.run_props))
    parts.append("</w:style>")
    return "".join(parts)


def styles_xml(catalog: StyleCatalog) -> str:
    body = [_doc_defaults_xml(catalog.defaults)]
    body.extend(_style_xml(style) for style in catalog.styles)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:styles xmlns:w="{W_NS}">'
        f'{"".join(body)}'
        "</w:styles>"
    )
