from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class RawRelation(BaseModel):
    name: str
    label: str  # 'spouse', 'child', 'parent', 'sibling', etc.


class Contact(BaseModel):
    uid: str
    first_name: str
    last_name: str
    display_name: str
    nickname: Optional[str] = None
    initials: str
    groups: list[str] = []
    phone_numbers: list[str] = []
    emails: list[str] = []
    birthday: Optional[str] = None    # ISO date: YYYY-MM-DD or --MM-DD (no year)
    anniversary: Optional[str] = None # ISO date: YYYY-MM-DD
    death_date: Optional[str] = None  # ISO date: YYYY-MM-DD; "0001-01-01" = deceased, date unknown
    notes: Optional[str] = None
    photo_url: Optional[str] = None  # e.g. "/photos/{uid}.jpg"
    interests: list[str] = []
    spouse_uid: Optional[str] = None
    children_uids: list[str] = []
    parent_uids: list[str] = []
    sibling_uids: list[str] = []
    raw_related: list[RawRelation] = []


class FamilyNode(BaseModel):
    """Recursive family tree node: a couple (or individual) and their sub-trees."""
    couple: list[str]               # 1 or 2 UIDs
    children: list['FamilyNode'] = []  # each child's own family sub-tree

FamilyNode.model_rebuild()  # required for self-referential Pydantic model


class GroupView(BaseModel):
    group: str
    trees: list[FamilyNode]  # root-level family trees
    singles: list[str]       # UIDs not in any family structure


class GroupSummary(BaseModel):
    name: str
    count: int


class UnresolvedRelation(BaseModel):
    contact_uid: str
    contact_name: str
    related_name: str
    label: str
    candidates: list[str] = []  # UIDs of ambiguous matches
    reason: str = "not_found"   # "not_found" | "out_of_scope" | "ambiguous"


class SyncResult(BaseModel):
    contacts_count: int
    groups_count: int
    unresolved_count: int


class AppSettings(BaseModel):
    default_group: Optional[str] = None
