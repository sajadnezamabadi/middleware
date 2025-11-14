from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from utils.acl.engine import ACLDecisionEngine
from utils.acl.builder import clear_routes_for_token


class Command(BaseCommand):
    help = "Invalidate cached ACL data (either endpoint-level or specific token routes)."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--endpoint", type=str, help="Endpoint UUID to invalidate from the ACL decision cache.")
        group.add_argument("--token", type=str, help="Raw access token string to clear cached routes for.")

    def handle(self, *args, **options):
        endpoint_id = options.get("endpoint")
        token = options.get("token")

        if endpoint_id:
            engine = ACLDecisionEngine()
            engine.invalidate_endpoint(endpoint_id)
            self.stdout.write(self.style.SUCCESS(f"Invalidated ACL cache for endpoint {endpoint_id}."))
            return

        if token:
            clear_routes_for_token(token)
            self.stdout.write(self.style.SUCCESS("Cleared cached routes for supplied token."))
            return

        raise CommandError("Either --endpoint or --token must be provided.")

