# lang_types.py
# Osnovne strukture: definicija klase i instance, plus pomoćna funkcija za int.

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import re

_INT_RE = re.compile(r"-?\d+$")


def is_int(tok: str) -> bool:
    """
    Proverava da li je token ceo broj (npr. '5', '-3').
    """
    return bool(_INT_RE.match(tok))


@dataclass
class ClassDef:
    """
    Opis jedne klase u jeziku.

    name      - ime klase (npr. 'A')
    base_name - ime bazne klase (string), razrešava se kasnije u base
    fields    - lista polja koja OVA klasa uvodi
    methods   - mapa: ime metode -> lista tokena koje ispisuje
    base      - referenca na baznu klasu (ClassDef) ili None
    """
    name: str
    base_name: Optional[str]
    fields: List[str]
    methods: Dict[str, List[str]]
    base: Optional["ClassDef"] = None  # popuni se posle parsiranja

    def all_fields(self) -> List[str]:
        """
        Vraća sva polja klase, uključujući nasleđena (baza pre izvedene).
        """
        if self.base is None:
            return list(self.fields)
        return self.base.all_fields() + self.fields

    def is_subclass_of(self, other: "ClassDef") -> bool:
        """
        Proverava da li je ova klasa jednaka ili potklasa zadate.
        """
        c: Optional[ClassDef] = self
        while c is not None:
            if c is other:
                return True
            c = c.base
        return False

    def lookup_method(self, name: str) -> Optional[List[str]]:
        """
        Traži metodu u ovoj klasi i bazama (prema hijerarhiji).
        Vraća listu tokena ako postoji, inače None.
        """
        c: Optional[ClassDef] = self
        while c is not None:
            if name in c.methods:
                return c.methods[name]
            c = c.base
        return None


@dataclass
class Instance:
    """
    Konkretna instanca objekta.

    cls    - stvarna (runtime) klasa objekta
    fields - mapa: ime polja -> vrednost (int)
    """
    cls: ClassDef
    fields: Dict[str, int]
