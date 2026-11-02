# compose_application

Optional composition of typed storage, APIs and spatial interfaces.

`compose_application` is the application integration home for **Cohesion Block A**.
It coordinates optional use of `backpack-store`, `expose-api` and `spatial-ui`,
with `enforce-type` validation and a pocket-python Track B application target.

- Repository: `outside-labs/compose_application`
- Distribution: `compose-application`
- Import: `compose_application`
- Python: 3.14 or newer
- Runtime dependencies: none in the initial package foundation

The component libraries remain independently useful and independently released.
Application profiles will explicitly select integrations and dependencies.
The current package is an installable foundation; application assembly APIs,
storage adapters, reference applications and browser runtime support are planned.

## Plan and development queue

- [Cohesion Block A Project](https://github.com/orgs/outside-labs/projects/18)
- [Architecture charter](docs/cohesion-block-a.md)
- [Shared contract register](docs/contracts.md)
- [Roadmap and owning issues](docs/roadmap.md)

Issues hold scope, acceptance criteria and dependencies. The organization Project
coordinates the repositories without replacing their existing development queues.
The initial batch establishes contracts, canonical storage naming, the validation
adapter and an extraction inventory of Pretty Notebook's storage behavior.

## Development

```sh
uv sync --locked
uv run --locked python scripts/check_distribution.py
```

The distribution check builds and installs both wheel and source distributions
into independent temporary environments outside the checkout. CI runs it on
Linux, macOS and Windows using Python 3.14.

No release has been published for this project. Package publication and hosted
deployment require their own selected scope and authorization. License terms
will be selected before publication.
