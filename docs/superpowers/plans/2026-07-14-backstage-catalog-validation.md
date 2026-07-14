# Backstage Catalog Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable validator and a fully connected Backstage catalog that finishes with zero validation errors.

**Architecture:** A dependency-free Ruby validator loads the root `Location` and its YAML targets, normalizes entity references, and applies structural and graph rules. Separate YAML files hold the Group, Domain, System, and Component entities, with `catalog-info.yaml` as the single entry point.

**Tech Stack:** Ruby standard library (`yaml`, `set`, `pathname`), Backstage catalog YAML

## Global Constraints

- Preserve `Component:default/my-first-service` and its existing GitHub annotation.
- Use `Group:default/kanenggg` for catalog ownership.
- Do not modify unrelated application files.
- Validation must exit nonzero for errors and print entity, error, and warning totals.

---

### Task 1: Catalog validator

**Files:**
- Create: `scripts/validate_catalog.rb`
- Create: `tests/test_validate_catalog.rb`

**Interfaces:**
- Consumes: a root catalog path passed as the first CLI argument, defaulting to `catalog-info.yaml`
- Produces: `CatalogValidator.new(root_path).validate`, returning a report hash with `entities`, `errors`, and `warnings`

- [ ] **Step 1: Write failing validator tests**

Use temporary fixtures and assert that the validator reports malformed YAML, invalid kinds, duplicate identities, uncovered targets, missing owners/systems/domains, broken references, and APIs with provider cardinality other than one. Also add a connected Group → Domain → System → Component fixture whose report has no errors.

```ruby
report = CatalogValidator.new(root).validate
assert_includes report[:errors], expected_message

clean_report = CatalogValidator.new(clean_root).validate
assert_empty clean_report[:errors]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `ruby tests/test_validate_catalog.rb`

Expected: failure because `scripts/validate_catalog.rb` does not exist.

- [ ] **Step 3: Implement the validator**

Implement these focused operations:

```ruby
SUPPORTED_KINDS = %w[API Component Domain Group Location Resource System Template User].freeze

def identity(entity)
  [entity.fetch('kind').downcase,
   entity.dig('metadata', 'namespace') || 'default',
   entity.dig('metadata', 'name')].join(':').downcase
end

def normalize_ref(ref, default_kind)
  kind, rest = ref.include?(':') ? ref.split(':', 2) : [default_kind, ref]
  namespace, name = rest.include?('/') ? rest.split('/', 2) : ['default', rest]
  [kind, namespace, name].join(':').downcase
end

def validate
  load_root_and_targets
  validate_required_fields
  validate_supported_kinds
  validate_unique_identities
  validate_root_coverage
  validate_ownership
  validate_hierarchy
  validate_explicit_references
  validate_api_provider_cardinality
  { entities: @entities.length, errors: @errors, warnings: @warnings }
end
```

Recognize references from `owner`, `system`, `domain`, `providesApis`, `consumesApis`, `dependsOn`, `dependencyOf`, `subcomponentOf`, `memberOf`, `parent`, and `children`. Treat only `Location` targets as root coverage; ignore YAML configuration files outside that target graph.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `ruby tests/test_validate_catalog.rb`

Expected: all tests pass with zero failures and zero errors.

- [ ] **Step 5: Demonstrate the current catalog failures**

Run: `ruby scripts/validate_catalog.rb catalog-info.yaml`

Expected: nonzero exit with errors for the invalid root shape, unresolved owner, and missing System relationship.

### Task 2: Connected catalog entity graph

**Files:**
- Modify: `catalog-info.yaml`
- Create: `catalog/group.yaml`
- Create: `catalog/domain.yaml`
- Create: `catalog/system.yaml`
- Create: `catalog/component.yaml`

**Interfaces:**
- Consumes: Backstage entity reference conventions enforced by Task 1
- Produces: one root Location covering four uniquely identified entity files

- [ ] **Step 1: Replace the root with explicit targets**

```yaml
apiVersion: backstage.io/v1alpha1
kind: Location
metadata:
  name: youtrack-python-catalog
spec:
  type: file
  targets:
    - ./catalog/group.yaml
    - ./catalog/domain.yaml
    - ./catalog/system.yaml
    - ./catalog/component.yaml
```

- [ ] **Step 2: Add Group, Domain, and System entities**

Use `group:default/kanenggg` as owner, `domain:default/developer-tools` as the System's domain, and valid Backstage fields for each kind. The Group will use `spec.type: team`, an empty `children` array, and profile display name `kanenggg`.

- [ ] **Step 3: Move the Component into its target file**

Preserve its name, description, lifecycle, service type, and GitHub annotation. Set:

```yaml
spec:
  owner: group:default/kanenggg
  system: system:default/youtrack-python
```

- [ ] **Step 4: Repeat validation until clean**

Run: `ruby scripts/validate_catalog.rb catalog-info.yaml`

Expected: `Entities: 5`, `Errors: 0`, and exit status 0. If errors remain, correct one root cause at a time and rerun the same command.

- [ ] **Step 5: Run the complete verification suite**

Run:

```bash
ruby tests/test_validate_catalog.rb
ruby scripts/validate_catalog.rb catalog-info.yaml
git diff --check
```

Expected: tests have zero failures/errors, catalog validation has zero errors, and `git diff --check` prints nothing.
