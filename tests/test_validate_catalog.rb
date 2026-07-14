# frozen_string_literal: true

require 'minitest/autorun'
require 'tmpdir'
require 'fileutils'
require_relative '../scripts/validate_catalog'

class CatalogValidatorTest < Minitest::Test
  def with_catalog(files)
    Dir.mktmpdir do |dir|
      files.each do |path, content|
        full_path = File.join(dir, path)
        FileUtils.mkdir_p(File.dirname(full_path))
        File.write(full_path, content)
      end
      yield File.join(dir, 'catalog-info.yaml')
    end
  end

  def validate(files)
    with_catalog(files) { |root| CatalogValidator.new(root).validate }
  end

  def location(*targets)
    <<~YAML
      apiVersion: backstage.io/v1alpha1
      kind: Location
      metadata:
        name: test-catalog
      spec:
        type: file
        targets:
      #{targets.map { |target| "    - #{target}" }.join("\n")}
    YAML
  end

  def valid_entities
    {
      'catalog-info.yaml' => location('./group.yaml', './domain.yaml', './system.yaml', './component.yaml', './api.yaml'),
      'group.yaml' => <<~YAML,
        apiVersion: backstage.io/v1alpha1
        kind: Group
        metadata:
          name: kanenggg
        spec:
          type: team
          children: []
      YAML
      'domain.yaml' => <<~YAML,
        apiVersion: backstage.io/v1alpha1
        kind: Domain
        metadata:
          name: developer-tools
        spec:
          owner: group:default/kanenggg
      YAML
      'system.yaml' => <<~YAML,
        apiVersion: backstage.io/v1alpha1
        kind: System
        metadata:
          name: youtrack-python
        spec:
          owner: group:default/kanenggg
          domain: domain:default/developer-tools
      YAML
      'component.yaml' => <<~YAML,
        apiVersion: backstage.io/v1alpha1
        kind: Component
        metadata:
          name: my-first-service
        spec:
          type: service
          lifecycle: experimental
          owner: group:default/kanenggg
          system: system:default/youtrack-python
          providesApis:
            - api:default/issues-api
      YAML
      'api.yaml' => <<~YAML
        apiVersion: backstage.io/v1alpha1
        kind: API
        metadata:
          name: issues-api
        spec:
          type: openapi
          lifecycle: experimental
          owner: group:default/kanenggg
          definition: |
            openapi: 3.0.0
            info:
              title: Issues API
              version: 1.0.0
            paths: {}
      YAML
    }
  end

  def test_accepts_a_fully_connected_catalog
    report = validate(valid_entities)

    assert_empty report[:errors], report[:errors].join("\n")
    assert_equal 6, report[:entities]
  end

  def test_reports_malformed_yaml
    files = valid_entities.merge('component.yaml' => "kind: Component\nmetadata: [\n")

    report = validate(files)

    assert report[:errors].any? { |error| error.include?('invalid YAML') }
  end

  def test_reports_invalid_kind_and_duplicate_identity
    files = valid_entities.merge(
      'component.yaml' => valid_entities['component.yaml'] + "---\napiVersion: backstage.io/v1alpha1\nkind: Widget\nmetadata:\n  name: odd\n",
      'api.yaml' => valid_entities['api.yaml'] + "---\n" + valid_entities['api.yaml']
    )

    report = validate(files)

    assert report[:errors].any? { |error| error.include?('invalid entity kind Widget') }
    assert report[:errors].any? { |error| error.include?('duplicate entity api:default:issues-api') }
  end

  def test_reports_uncovered_entity_file
    files = valid_entities.merge('orphan.yaml' => <<~YAML)
      apiVersion: backstage.io/v1alpha1
      kind: Resource
      metadata:
        name: orphan
      spec:
        type: database
        owner: group:default/kanenggg
    YAML

    report = validate(files)

    assert report[:errors].any? { |error| error.include?('catalog-info.yaml does not reference orphan.yaml') }
  end

  def test_reports_missing_hierarchy_and_broken_owner
    component = valid_entities['component.yaml'].gsub('group:default/kanenggg', 'group:default/missing').sub(/^  system:.*\n/, '')
    system = valid_entities['system.yaml'].sub(/^  domain:.*\n/, '')
    files = valid_entities.merge('component.yaml' => component, 'system.yaml' => system)

    report = validate(files)

    assert report[:errors].any? { |error| error.include?('broken owner reference group:default/missing') }
    assert report[:errors].any? { |error| error.include?('missing system') }
    assert report[:errors].any? { |error| error.include?('missing domain') }
  end

  def test_reports_missing_owner_and_broken_generic_reference
    api = valid_entities['api.yaml'].sub(/^  owner:.*\n/, '').sub("  definition: |\n", "  dependsOn:\n    - resource:default/missing-db\n  definition: |\n")
    files = valid_entities.merge('api.yaml' => api)

    report = validate(files)

    assert report[:errors].any? { |error| error.include?('missing owner') }
    assert report[:errors].any? { |error| error.include?('broken dependsOn reference resource:default/missing-db') }
  end

  def test_reports_api_provider_cardinality
    component = valid_entities['component.yaml'].sub(/  providesApis:\n    - api:default\/issues-api\n/, '')
    files = valid_entities.merge('component.yaml' => component)

    report = validate(files)

    assert report[:errors].any? { |error| error.include?('API api:default:issues-api is provided by 0 Components') }
  end

  def test_reports_broken_optional_system_reference
    files = valid_entities.merge('resource.yaml' => <<~YAML)
      apiVersion: backstage.io/v1alpha1
      kind: Resource
      metadata:
        name: postgres
      spec:
        type: database
        owner: group:default/kanenggg
        system: system:default/missing
    YAML
    files['catalog-info.yaml'] = location(
      './group.yaml', './domain.yaml', './system.yaml', './component.yaml', './api.yaml', './resource.yaml'
    )

    report = validate(files)

    assert report[:errors].any? { |error| error.include?('broken system reference system:default/missing') }
  end
end
