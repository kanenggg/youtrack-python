# Backstage Catalog Validation Design

## Goal

Create a valid, self-contained Backstage catalog whose root file references every entity and whose ownership and hierarchy references resolve without ambiguity.

## Catalog structure

`catalog-info.yaml` will contain a `Location` entity with explicit local targets for these entity files:

- `catalog/component.yaml`: `Component:default/my-first-service`
- `catalog/system.yaml`: `System:default/youtrack-python`
- `catalog/domain.yaml`: `Domain:default/developer-tools`
- `catalog/group.yaml`: `Group:default/kanenggg`

The component will be owned by `group:default/kanenggg` and belong to `system:default/youtrack-python`. The system will be owned by the same group and belong to `domain:default/developer-tools`. The domain will also be owned by that group.

The application `auth` configuration currently embedded in `catalog-info.yaml` is outside the catalog entity model and will be removed from the catalog.

## Validation

A repository-local validator will load all catalog YAML documents and report:

- YAML syntax failures
- unsupported entity kinds
- duplicate entity identities, using kind, namespace, and name
- root `Location` targets that are missing or fail to cover an entity file
- missing `spec.owner` fields and unresolved owner references
- Components without valid System references
- Systems without valid Domain references
- broken explicit entity references
- APIs referenced by zero or more than one Component

References will be normalized using Backstage's default namespace and kind rules where shorthand references are allowed. Validation will exit nonzero when errors exist and print a concise report with entity and error counts.

## Implementation and verification

First, the validator will be introduced and run against the current catalog to demonstrate the known failures. Then the catalog will be reorganized into the entity graph above. Validation will be repeated after each correction until it exits successfully with zero errors. Existing unrelated repository files and user changes will remain untouched.

## Success criteria

- Every YAML file used by the catalog parses successfully.
- Every catalog entity has a supported kind and unique identity.
- `catalog-info.yaml` targets every entity file exactly once.
- Every ownership, System, Domain, and API reference resolves and satisfies its required cardinality.
- The final validation report contains zero errors.
