# Releasing `iata-dangerous-goods`

Releases are published from GitHub Releases through PyPI Trusted Publishing.
No long-lived PyPI API token is stored in GitHub.

## One-time PyPI setup

Before the first release, create a pending Trusted Publisher for the project
name `iata-dangerous-goods` on PyPI with these values:

- PyPI project name: `iata-dangerous-goods`
- GitHub owner: `theo-bender`
- GitHub repository: `iata-dangerous-goods`
- Workflow filename: `release.yml`
- Environment name: `pypi`

Create a matching `pypi` environment in the GitHub repository. Adding a
required reviewer to that environment is recommended so publishing requires an
explicit approval.

## Prepare a release

1. Update `project.version` in `pyproject.toml`.
2. Run the tests:

   ```powershell
   python -m unittest discover -v
   ```

3. Build and validate the archives:

   ```powershell
   python -m build
   python -m twine check dist/*
   ```

4. Install the wheel into a clean environment and run an import check.
5. Merge the version change into `main`.

## Publish

Create and publish a GitHub Release whose tag matches the version with a `v`
prefix, for example `v0.1.0`. Publishing the GitHub Release triggers
`.github/workflows/release.yml`, which builds fresh archives and uploads them
to PyPI using the configured Trusted Publisher.

PyPI does not allow a filename or version to be replaced. If publishing fails
after any archive was accepted, increment the version before trying again.
