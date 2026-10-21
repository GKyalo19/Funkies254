"""Shared fetch result. Concrete fetchers live beside this module."""

from dataclasses import dataclass


@dataclass
class RawPage:
    url: str
    text: str
    html: str = ""
