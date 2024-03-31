"""
This file defines some DOCUMENT classes for parsing
"""
from typing import List
from dataclasses import dataclass, field

@dataclass
class Element:
    parent: "Element" = None
    children: List["Element"] = field(default_factory=list)

    @property
    def plain_text(self):
        return "".join([child.plain_text for child in self.children])
    
    def append(self, child: "Element") -> "Element":
        self.children.append(child)
        child.parent = self
        return child

  
class
