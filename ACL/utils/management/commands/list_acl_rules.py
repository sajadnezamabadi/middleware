from __future__ import annotations

from django.core.management.base import BaseCommand

from utils.models import ACLRule, Endpoint


class Command(BaseCommand):
    help = "List ACL rules grouped by endpoint and subject."

    def add_arguments(self, parser):
        parser.add_argument(
            "--endpoint",
            type=str,
            help="Filter by endpoint path pattern (supports substring match).",
        )
        parser.add_argument(
            "--role",
            type=str,
            help="Filter by role choice (exact match).",
        )
        parser.add_argument(
            "--team",
            type=str,
            help="Filter by team name (exact match on Team.name_en).",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Filter by user identifier (UUID).",
        )

    def handle(self, *args, **options):
        queryset = ACLRule.objects.select_related("endpoint", "team", "user").order_by(
            "endpoint__path_pattern",
            "-priority",
        )

        endpoint_filter = options.get("endpoint")
        if endpoint_filter:
            queryset = queryset.filter(endpoint__path_pattern__icontains=endpoint_filter)

        role_filter = options.get("role")
        if role_filter:
            queryset = queryset.filter(role=role_filter)

        team_filter = options.get("team")
        if team_filter:
            queryset = queryset.filter(team__name_en=team_filter)

        user_filter = options.get("user")
        if user_filter:
            queryset = queryset.filter(user_id=user_filter)

        if not queryset.exists():
            self.stdout.write(self.style.WARNING("No ACL rules found with the given filters."))
            return

        current_endpoint = None
        for rule in queryset:
            if current_endpoint != rule.endpoint_id:
                self.stdout.write("")
                self.stdout.write(self.style.NOTICE(f"Endpoint: {rule.endpoint.path_pattern} [{rule.endpoint.method}]"))
                current_endpoint = rule.endpoint_id

            subject_parts = []
            if rule.user_id:
                subject_parts.append(f"user={rule.user_id}")
            if rule.role:
                subject_parts.append(f"role={rule.role}")
            if rule.team_id:
                subject_parts.append(f"team={rule.team.name_en if rule.team else rule.team_id}")
            subject = ", ".join(subject_parts) or "unknown subject"

            status = "ALLOW" if rule.allow else "DENY"
            self.stdout.write(f"  - {status:<5} priority={rule.priority:<3} {subject}")

