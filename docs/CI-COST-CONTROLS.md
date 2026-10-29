# GitHub Actions cost-control policy

This repository prioritizes avoiding unexpected GitHub Actions charges.

## When tests run

- Feature-branch pushes: **no automatic hosted CI**.
- Draft pull-request creation and subsequent draft updates: **no automatic hosted CI**.
- Marking a pull request ready for review: full Python 3.13 and 3.14 test matrix.
- Pushes to `develop`: full Python matrix.
- `workflow_dispatch`: manually run full matrix at a deliberate checkpoint.

The workflow cancels superseded in-progress runs on the same ref and has a
10-minute timeout per matrix job. These controls reduce runner usage; they
do not guarantee that a GitHub account cannot incur charges.

## Development practice

1. Combine related changes into substantive batches rather than one commit per
   small test or documentation edit.
2. Review code and run inexpensive local checks where possible.
3. Use hosted CI at integration checkpoints, not after every file update.
4. Check the GitHub Actions usage meter periodically. Before enabling any
   additional hosted runners, paid services, or deployment infrastructure,
   obtain explicit owner approval.
5. Keep the PR draft until a review checkpoint is intentionally scheduled.
6. Do not change the existing live homelab during CI work.

## Owner-controlled billing safeguard

In GitHub's billing settings, inspect Actions usage, budgets, payment methods,
and spending limits. Configure a **$0 budget with stop-usage enforcement**
if that option is available for this account. Budget alerts alone are not
the same as hard spending enforcement. The GitHub repository connector does
not grant account billing access, so this safeguard must be confirmed by the
account owner. Do not assume it is already configured.

## Manual run

From the repository's Actions tab, choose **Python tests**, then
**Run workflow**, select the intended branch and confirm. The workflow file
may need to be present on the repository's default branch for GitHub to expose
manual dispatch in the UI; until then, use the repository's available
review-triggered workflow or ask for an explicit CI plan.
