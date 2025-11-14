from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from django.conf import settings

from utils.acl.cache import RedisCache
from utils.models import ACLRule


class ACLDecisionEngine:
    """
    Evaluate ACL rules for a given endpoint and staff member.
    Priority order:
      1. User-specific rules
      2. Role-based rules
      3. Team-based rules (highest priority wins)
    Deny by default when no rule matches.
    """

    def __init__(self, cache: Optional[RedisCache] = None) -> None:
        self.cache = cache or RedisCache()
        self.ttl = getattr(settings, "ACL_CACHE_TTL", 3600)

    def is_allowed(self, staff, endpoint_payload: Dict[str, Any]) -> bool:
        if staff is None:
            return False

        endpoint_id = endpoint_payload.get("id")
        if not endpoint_id:
            return False

        rules = self._load_rules(endpoint_id)
        if not rules:
            return False

        user_rule = self._match_user_rule(rules, staff)
        if user_rule is not None:
            return user_rule

        role_rule = self._match_role_rule(rules, staff)
        if role_rule is not None:
            return role_rule

        team_rule = self._match_team_rule(rules, staff)
        if team_rule is not None:
            return team_rule

        return False

    def invalidate_endpoint(self, endpoint_id: str) -> None:
        key = self._cache_key(endpoint_id)
        self.cache.delete(key)

    def _load_rules(self, endpoint_id: str) -> List[Dict[str, Any]]:
        key = self._cache_key(endpoint_id)
        rules = self.cache.get_json(key)
        if rules is not None:
            return rules

        queryset = (
            ACLRule.objects.filter(endpoint_id=endpoint_id)
            .order_by("-priority", "id")
            .values("user_id", "role", "team_id", "allow", "priority")
        )
        serialized = self._serialize_rules(queryset)
        self.cache.set_json(key, serialized, ex=self.ttl)
        return serialized

    def _serialize_rules(self, queryset: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        serialized: List[Dict[str, Any]] = []
        for rule in queryset:
            if rule["user_id"]:
                serialized.append(
                    {"type": "user", "subject_id": str(rule["user_id"]), "allow": bool(rule["allow"]), "priority": rule["priority"]}
                )
            elif rule["role"]:
                serialized.append(
                    {"type": "role", "subject_id": rule["role"], "allow": bool(rule["allow"]), "priority": rule["priority"]}
                )
            elif rule["team_id"]:
                serialized.append(
                    {"type": "team", "subject_id": str(rule["team_id"]), "allow": bool(rule["allow"]), "priority": rule["priority"]}
                )
        return serialized

    def _match_user_rule(self, rules: List[Dict[str, Any]], staff) -> Optional[bool]:
        staff_id = str(staff.pk)
        candidates = [r for r in rules if r["type"] == "user" and r["subject_id"] == staff_id]
        return self._select_rule(candidates)

    def _match_role_rule(self, rules: List[Dict[str, Any]], staff) -> Optional[bool]:
        if not staff.role:
            return None
        candidates = [r for r in rules if r["type"] == "role" and r["subject_id"] == staff.role]
        return self._select_rule(candidates)

    def _match_team_rule(self, rules: List[Dict[str, Any]], staff) -> Optional[bool]:
        try:
            team_ids = list(staff.team.values_list("pk", flat=True))
        except Exception:
            team_ids = []

        if not team_ids:
            return None

        team_ids = [str(pk) for pk in team_ids]
        candidates = [r for r in rules if r["type"] == "team" and r["subject_id"] in team_ids]
        return self._select_rule(candidates)

    def _select_rule(self, candidates: List[Dict[str, Any]]) -> Optional[bool]:
        if not candidates:
            return None
        ordered = sorted(candidates, key=lambda r: (r.get("priority", 0), r["allow"]), reverse=True)
        return bool(ordered[0]["allow"])

    def _cache_key(self, endpoint_id: str) -> str:
        return f"acl:endpoint:{endpoint_id}"

