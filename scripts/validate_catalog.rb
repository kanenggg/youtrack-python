#!/usr/bin/env ruby
# frozen_string_literal: true

require 'pathname'
require 'set'
require 'yaml'

class CatalogValidator
  SUPPORTED_KINDS = %w[API Component Domain Group Location Resource System Template User].freeze
  OWNED_KINDS = %w[API Component Domain Resource System Template].freeze
  TOP_LEVEL_KEYS = %w[apiVersion kind metadata spec relations status].freeze
  REFERENCE_FIELDS = {
    'owner' => 'Group',
    'system' => 'System',
    'domain' => 'Domain',
    'providesApis' => 'API',
    'consumesApis' => 'API',
    'dependsOn' => 'Component',
    'dependencyOf' => 'Component',
    'subcomponentOf' => 'Component',
    'memberOf' => 'Group',
    'parent' => 'Group',
    'children' => 'Group'
  }.freeze

  attr_reader :root_path

  def initialize(root_path = 'catalog-info.yaml')
    @root_path = Pathname(root_path).expand_path
    @base_dir = @root_path.dirname
    @errors = []
    @warnings = []
    @documents_by_file = {}
    @entities = []
    @entity_files = Set.new
    @index = {}
  end

  def validate
    load_all_yaml
    load_entities
    validate_root
    validate_required_fields
    validate_supported_kinds
    validate_top_level_keys
    index_entities
    validate_root_coverage
    validate_ownership
    validate_hierarchy
    validate_explicit_references
    validate_api_provider_cardinality

    {
      entities: @entities.length,
      yaml_files: @documents_by_file.length,
      errors: @errors.uniq.sort,
      warnings: @warnings.uniq.sort
    }
  end

  private

  def load_all_yaml
    yaml_paths.each do |path|
      begin
        @documents_by_file[path] = YAML.load_stream(path.read).compact
      rescue StandardError => e
        @documents_by_file[path] = []
        @errors << "#{relative(path)}: invalid YAML (#{e.message.lines.first.strip})"
      end
    end
  end

  def yaml_paths
    paths = Dir.glob(@base_dir.join('**', '*.{yaml,yml}').to_s, File::FNM_EXTGLOB)
    paths.reject { |path| path.include?('/.git/') || path.include?('/.worktrees/') }
         .map { |path| Pathname(path).expand_path }
         .sort
  end

  def load_entities
    @documents_by_file.each do |path, documents|
      documents.each_with_index do |document, index|
        next unless entity_document?(document)

        @entities << { entity: document, path: path, document: index + 1 }
        @entity_files << path unless path == @root_path
      end
    end
  end

  def entity_document?(document)
    document.is_a?(Hash) && (document.key?('apiVersion') || document.key?('kind') || document.key?('metadata'))
  end

  def validate_root
    unless @documents_by_file.key?(@root_path)
      @errors << "#{relative(@root_path)}: root catalog file is missing"
      return
    end

    root_entities = @entities.select { |item| item[:path] == @root_path }
    if root_entities.length != 1 || root_entities.first&.dig(:entity, 'kind') != 'Location'
      @errors << "#{relative(@root_path)}: root catalog must contain exactly one Location entity"
    end
  end

  def validate_required_fields
    @entities.each do |item|
      entity = item[:entity]
      location = label(item)
      @errors << "#{location}: missing apiVersion" if blank?(entity['apiVersion'])
      @errors << "#{location}: missing kind" if blank?(entity['kind'])
      @errors << "#{location}: missing metadata.name" if blank?(entity.dig('metadata', 'name'))
      @errors << "#{location}: spec must be a mapping" unless entity['spec'].is_a?(Hash)
    end
  end

  def validate_supported_kinds
    @entities.each do |item|
      kind = item[:entity]['kind']
      next if blank?(kind) || SUPPORTED_KINDS.include?(kind)

      @errors << "#{label(item)}: invalid entity kind #{kind}"
    end
  end

  def validate_top_level_keys
    @entities.each do |item|
      extras = item[:entity].keys.map(&:to_s) - TOP_LEVEL_KEYS
      extras.each { |key| @errors << "#{label(item)}: invalid top-level field #{key}" }
    end
  end

  def index_entities
    grouped = @entities.group_by { |item| identity(item[:entity]) }.reject { |key, _| key.nil? }
    grouped.each do |key, items|
      @index[key] = items.first
      next unless items.length > 1

      locations = items.map { |item| label(item) }.join(', ')
      @errors << "duplicate entity #{key} at #{locations}"
    end
  end

  def validate_root_coverage
    root = @entities.find { |item| item[:path] == @root_path && item[:entity]['kind'] == 'Location' }
    return unless root

    targets = root[:entity].dig('spec', 'targets')
    unless targets.is_a?(Array)
      @errors << "#{relative(@root_path)}: Location spec.targets must be an array"
      return
    end

    resolved = targets.map { |target| @base_dir.join(target.to_s).cleanpath.expand_path }
    resolved.group_by(&:itself).each do |path, occurrences|
      @errors << "#{relative(@root_path)}: duplicate target #{relative(path)}" if occurrences.length > 1
      @errors << "#{relative(@root_path)}: broken target #{relative(path)}" unless path.file?
    end

    @entity_files.each do |path|
      count = resolved.count(path)
      @errors << "#{relative(@root_path)} does not reference #{relative(path)}" if count.zero?
      @errors << "#{relative(@root_path)} references #{relative(path)} #{count} times" if count > 1
    end

    resolved.each do |path|
      next unless path.file? && !@documents_by_file.fetch(path, []).none?
      next if @entity_files.include?(path)

      @warnings << "#{relative(@root_path)} targets #{relative(path)}, which contains no catalog entity"
    end
  end

  def validate_ownership
    @entities.each do |item|
      entity = item[:entity]
      next unless OWNED_KINDS.include?(entity['kind'])

      owner = entity.dig('spec', 'owner')
      if blank?(owner)
        @errors << "#{entity_label(entity)}: missing owner"
        next
      end

      normalized = normalize_ref(owner, 'Group')
      target = @index[normalized]
      unless target && %w[Group User].include?(target[:entity]['kind'])
        @errors << "#{entity_label(entity)}: broken owner reference #{display_ref(normalized)}"
      end
    end
  end

  def validate_hierarchy
    entities_of_kind('Component').each do |item|
      validate_required_reference(item[:entity], 'system', 'System')
    end
    entities_of_kind('System').each do |item|
      validate_required_reference(item[:entity], 'domain', 'Domain')
    end
  end

  def validate_required_reference(entity, field, kind)
    value = entity.dig('spec', field)
    if blank?(value)
      @errors << "#{entity_label(entity)}: missing #{field}"
      return
    end

    normalized = normalize_ref(value, kind)
    target = @index[normalized]
    return if target && target[:entity]['kind'] == kind

    @errors << "#{entity_label(entity)}: broken #{field} reference #{display_ref(normalized)}"
  end

  def validate_explicit_references
    @entities.each do |item|
      entity = item[:entity]
      spec = entity['spec']
      next unless spec.is_a?(Hash)

      REFERENCE_FIELDS.each do |field, default_kind|
        next if field == 'owner'
        next unless spec.key?(field)

        values = spec[field].is_a?(Array) ? spec[field] : [spec[field]]
        values.each do |value|
          next if blank?(value)

          normalized = normalize_ref(value, default_kind)
          next if @index.key?(normalized)

          @errors << "#{entity_label(entity)}: broken #{field} reference #{display_ref(normalized)}"
        end
      end
    end
  end

  def validate_api_provider_cardinality
    providers = Hash.new { |hash, key| hash[key] = [] }
    entities_of_kind('Component').each do |item|
      Array(item[:entity].dig('spec', 'providesApis')).each do |reference|
        providers[normalize_ref(reference, 'API')] << identity(item[:entity])
      end
    end

    entities_of_kind('API').each do |item|
      api_identity = identity(item[:entity])
      count = providers[api_identity].length
      next if count == 1

      @errors << "API #{api_identity} is provided by #{count} Components (expected exactly 1)"
    end
  end

  def entities_of_kind(kind)
    @entities.select { |item| item[:entity]['kind'] == kind }
  end

  def identity(entity)
    kind = entity['kind']
    name = entity.dig('metadata', 'name')
    return nil if blank?(kind) || blank?(name)

    namespace = entity.dig('metadata', 'namespace') || 'default'
    [kind, namespace, name].join(':').downcase
  end

  def normalize_ref(reference, default_kind)
    string = reference.to_s.strip
    kind, rest = string.include?(':') ? string.split(':', 2) : [default_kind, string]
    namespace, name = rest.include?('/') ? rest.split('/', 2) : ['default', rest]
    [kind, namespace, name].join(':').downcase
  end

  def display_ref(normalized)
    kind, namespace, name = normalized.split(':', 3)
    "#{kind}:#{namespace}/#{name}"
  end

  def entity_label(entity)
    identity(entity) || "unknown entity"
  end

  def label(item)
    suffix = @documents_by_file.fetch(item[:path], []).length > 1 ? " document #{item[:document]}" : ''
    "#{relative(item[:path])}#{suffix}"
  end

  def relative(path)
    Pathname(path).expand_path.relative_path_from(@base_dir).to_s
  rescue ArgumentError
    path.to_s
  end

  def blank?(value)
    value.nil? || (value.respond_to?(:empty?) && value.empty?)
  end
end

if $PROGRAM_NAME == __FILE__
  report = CatalogValidator.new(ARGV[0] || 'catalog-info.yaml').validate
  puts 'Catalog validation report'
  puts "YAML files: #{report[:yaml_files]}"
  puts "Entities: #{report[:entities]}"
  puts "Errors: #{report[:errors].length}"
  report[:errors].each { |error| puts "  ERROR: #{error}" }
  puts "Warnings: #{report[:warnings].length}"
  report[:warnings].each { |warning| puts "  WARNING: #{warning}" }
  exit(report[:errors].empty? ? 0 : 1)
end
