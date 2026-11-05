import unittest

from fastapi.testclient import TestClient

from dashboard_ui import router
from fastapi import FastAPI


class DashboardAgentControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)
        cls.page = cls.client.get("/admin/dashboard").text

    def test_approval_control_exists(self):
        self.assertIn("Approve agent", self.page)
        self.assertIn("manageAgent(a,'approve',approve)", self.page)

    def test_revocation_control_exists(self):
        self.assertIn("Revoke identity", self.page)
        self.assertIn("manageAgent(a,'revoke',revoke)", self.page)

    def test_admin_bearer_authentication(self):
        self.assertIn("Authorization:'Bearer '+actionCredential", self.page)
        self.assertIn("const actionCredential=credential", self.page)
        self.assertIn("Administrator authentication required.", self.page)

    def test_confirmation_required(self):
        self.assertIn("window.confirm(warning)", self.page)
        self.assertIn("else if(!window.confirm(warning))", self.page)

    def test_revocation_warning(self):
        self.assertIn("PERMANENTLY revoke", self.page)
        self.assertIn("This identity cannot be approved again.", self.page)

    def test_revocation_requires_typed_confirmation(self):
        self.assertIn("window.prompt(", self.page)
        self.assertIn("typed!=='REVOKE'", self.page)
        self.assertIn("Revocation cancelled.", self.page)

    def test_approval_retains_confirmation(self):
        self.assertIn("window.confirm(warning)", self.page)

    def test_lifecycle_requests_are_serialized(self):
        self.assertIn("let lifecycleBusy=false", self.page)
        self.assertIn("if(lifecycleBusy)return", self.page)
        self.assertIn("lifecycleBusy=true", self.page)
        self.assertIn("finally{", self.page)

    def test_successful_mutation_refresh_failure_is_distinguished(self):
        self.assertIn("mutationSucceeded=true", self.page)
        self.assertIn("Agent action succeeded, but fleet refresh failed.", self.page)
        self.assertIn("inventory=[]", self.page)

    def test_only_expected_lifecycle_actions(self):
        self.assertIn("a.status==='pending'", self.page)
        self.assertIn("a.status==='approved'", self.page)
        self.assertIn("method:'POST'", self.page)
        self.assertNotIn("method:'DELETE'", self.page)
        self.assertNotIn("method:'PUT'", self.page)

    def test_no_package_management_actions(self):
        self.assertIn(
            "No scans, package installations, reboots, or deployments",
            self.page,
        )

    def test_token_not_persisted_in_browser_storage(self):
        self.assertNotIn("localStorage", self.page)
        self.assertNotIn("sessionStorage", self.page)

    def test_dashboard_security_headers(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-frame-options"], "DENY")


if __name__ == "__main__":
    unittest.main()
