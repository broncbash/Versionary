"""Verify dashboard lifecycle API compatibility with the isolated HTTPS beta.

These tests inspect the actual application router definitions.
They do not initialize persistent state, start servers, or mutate agents.
"""

import unittest

from dashboard_ui import PAGE
from admin_agents_api import router as inventory_router
from versionary_https_beta_admin import router as lifecycle_router
from dashboard_ui import router as dashboard_router


def registered_routes(router):
    """Return the full HTTP methods and paths exposed by a router."""
    return {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


class DashboardBetaRouteCompatibilityTests(unittest.TestCase):

    def test_dashboard_uses_admin_lifecycle_namespace(self):
        expected = (
            "'/api/v1/admin/agents/'+"
            "encodeURIComponent(agent.id)+'/'+action"
        )

        self.assertIn(expected, PAGE)

        self.assertNotIn(
            "'/api/v1/agents/'+encodeURIComponent(agent.id)+'/'+action",
            PAGE,
        )

    def test_beta_routers_expose_dashboard_dependencies(self):
        routes = set()

        for router in (
            inventory_router,
            lifecycle_router,
            dashboard_router,
        ):
            routes.update(registered_routes(router))

        expected = {
            ("GET", "/admin/dashboard"),
            ("GET", "/api/v1/admin/agents"),
            ("POST", "/api/v1/admin/agents/{agent_id}/approve"),
            ("POST", "/api/v1/admin/agents/{agent_id}/revoke"),
        }

        self.assertTrue(
            expected.issubset(routes),
            f"Missing dashboard routes: {expected - routes}",
        )


if __name__ == "__main__":
    unittest.main()
