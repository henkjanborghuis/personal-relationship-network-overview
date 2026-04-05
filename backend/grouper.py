"""
Builds a recursive family tree (GroupView) from a set of contacts.
"""
from models import Contact, FamilyNode, GroupView


def _couple_for(uid: str, contacts: dict[str, Contact], available: set[str]) -> list[str]:
    """Return [uid, spouse_uid] if spouse is available, else [uid]."""
    c = contacts[uid]
    if c.spouse_uid and c.spouse_uid in available:
        return [uid, c.spouse_uid]
    return [uid]


def _find_co_parent_pairs(uids: set[str], contacts: dict[str, Contact], uid_set: set[str]) -> list[list[str]]:
    """
    Among `uids`, find pairs who share a child in uid_set but have no explicit spouse link.
    Returns a list of [p1, p2] pairs.
    """
    child_to_parents: dict[str, list[str]] = {}
    for uid in uids:
        for child_uid in contacts[uid].children_uids:
            if child_uid in uid_set:
                child_to_parents.setdefault(child_uid, []).append(uid)

    pairs: list[list[str]] = []
    seen: set[frozenset] = set()
    for parents in child_to_parents.values():
        unaccounted = [p for p in parents if p in uids]
        if len(unaccounted) == 2:
            key = frozenset(unaccounted)
            if key not in seen:
                seen.add(key)
                pairs.append(unaccounted)
    return pairs


def _group_into_units(uids: set[str], contacts: dict[str, Contact], uid_set: set[str]) -> list[list[str]]:
    """
    Group a set of UIDs into family units: explicit couples first,
    then co-parents, then singletons.
    Returns a list of [uid] or [uid1, uid2] lists.
    """
    accounted: set[str] = set()
    units: list[list[str]] = []

    # Explicit spouse pairs
    for uid in sorted(uids):  # sorted for determinism
        if uid in accounted:
            continue
        c = contacts[uid]
        if c.spouse_uid and c.spouse_uid in uids and c.spouse_uid not in accounted:
            units.append([uid, c.spouse_uid])
            accounted.update([uid, c.spouse_uid])

    # Co-parent pairs (share a child in the broader group)
    remaining = uids - accounted
    for pair in _find_co_parent_pairs(remaining, contacts, uid_set):
        p1, p2 = pair
        if p1 not in accounted and p2 not in accounted:
            units.append([p1, p2])
            accounted.update([p1, p2])

    # Remaining singletons
    for uid in sorted(uids - accounted):
        units.append([uid])

    return units


def _build_node(
    couple: list[str],
    contacts: dict[str, Contact],
    uid_set: set[str],
    accounted: set[str],
) -> FamilyNode:
    """Recursively build a FamilyNode for a couple/individual."""
    # Find all children of this unit who are in the group and not yet placed
    raw_children: set[str] = set()
    for uid in couple:
        raw_children.update(
            c for c in contacts[uid].children_uids
            if c in uid_set and c not in accounted
        )

    if not raw_children:
        return FamilyNode(couple=couple, children=[])

    # For each child, include their spouse (if in the group and unaccounted)
    child_units: list[list[str]] = []
    accounted_in_children: set[str] = set()

    # Build units for children — each child with their spouse (if any in group)
    for child_uid in sorted(raw_children):
        if child_uid in accounted_in_children:
            continue
        child = contacts[child_uid]
        spouse_uid = child.spouse_uid
        if spouse_uid and spouse_uid in uid_set and spouse_uid not in accounted and spouse_uid not in accounted_in_children:
            child_units.append([child_uid, spouse_uid])
            accounted_in_children.update([child_uid, spouse_uid])
        else:
            child_units.append([child_uid])
            accounted_in_children.add(child_uid)

    # Also check for co-parent pairs among the raw_children + their spouses
    # (handles case where two children co-parent a grandchild with no explicit spouse link)
    all_child_uids = accounted_in_children.copy()
    extra_pairs = _find_co_parent_pairs(
        {u for unit in child_units if len(unit) == 1 for u in unit},
        contacts, uid_set
    )
    for pair in extra_pairs:
        p1, p2 = pair
        if p1 not in accounted and p2 not in accounted:
            # Replace the two singletons with a pair
            child_units = [u for u in child_units if u != [p1] and u != [p2]]
            child_units.append([p1, p2])

    # Mark all child-level UIDs as accounted before recursing
    accounted.update(all_child_uids)

    child_nodes = [
        _build_node(unit, contacts, uid_set, accounted)
        for unit in child_units
    ]

    return FamilyNode(couple=couple, children=child_nodes)


def _find_sibling_groups(
    root_units: list[list[str]],
    contacts: dict[str, Contact],
) -> list[list[int]]:
    """
    Return connected components of root_units indices linked by sibling_uids.
    Each component is a list of indices into root_units.
    """
    uid_to_idx: dict[str, int] = {}
    for i, unit in enumerate(root_units):
        for uid in unit:
            uid_to_idx[uid] = i

    adj: dict[int, set[int]] = {i: set() for i in range(len(root_units))}
    for i, unit in enumerate(root_units):
        for uid in unit:
            for sib in contacts[uid].sibling_uids:
                if sib in uid_to_idx:
                    j = uid_to_idx[sib]
                    if j != i:
                        adj[i].add(j)
                        adj[j].add(i)

    visited: set[int] = set()
    groups: list[list[int]] = []
    for start in range(len(root_units)):
        if start in visited:
            continue
        group: list[int] = []
        queue = [start]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            group.append(curr)
            queue.extend(adj[curr] - visited)
        groups.append(group)
    return groups


def build_group_view(group_name: str, contacts: dict[str, Contact], *, group_siblings: bool = True) -> GroupView:
    uid_set = set(contacts.keys())

    # A UID is a "child of the group" if at least one of its parents is in the group
    children_of_group = {
        uid for uid in uid_set
        if any(p in uid_set for p in contacts[uid].parent_uids)
    }

    # Spouses of children are NOT independent roots — they attach via the child's node
    spouses_of_children = {
        contacts[uid].spouse_uid
        for uid in children_of_group
        if contacts[uid].spouse_uid and contacts[uid].spouse_uid in uid_set
    }

    true_roots = uid_set - children_of_group - spouses_of_children

    # Group roots into couple/co-parent units
    root_units = _group_into_units(true_roots, contacts, uid_set)

    accounted: set[str] = set(uid for unit in root_units for uid in unit)

    if group_siblings:
        sibling_groups = _find_sibling_groups(root_units, contacts)
        trees: list[FamilyNode] = []
        for grp in sibling_groups:
            if len(grp) == 1:
                trees.append(_build_node(root_units[grp[0]], contacts, uid_set, accounted))
            else:
                child_nodes = [
                    _build_node(root_units[i], contacts, uid_set, accounted)
                    for i in sorted(grp)
                ]
                trees.append(FamilyNode(couple=[], children=child_nodes))
    else:
        trees = [_build_node(unit, contacts, uid_set, accounted) for unit in root_units]

    singles = [uid for uid in uid_set if uid not in accounted]

    return GroupView(group=group_name, trees=trees, singles=singles)


def build_all_group_views(all_contacts: dict[str, Contact]) -> dict[str, GroupView]:
    all_groups: set[str] = set()
    for c in all_contacts.values():
        all_groups.update(c.groups)

    return {
        name: build_group_view(
            name,
            {uid: c for uid, c in all_contacts.items() if name in c.groups},
        )
        for name in all_groups
    }
