#!/usr/bin/env ruby

require "csv"
require "date"
require "digest"
require "fileutils"
require "json"
require "time"
require "yaml"

INPUT = ARGV.fetch(0)
ROOT = File.expand_path("..", __dir__)
SOURCE_DIR = File.join(ROOT, "source")
DATA_DIR = File.join(ROOT, "data")
DOCS_DIR = File.join(ROOT, "docs")

FileUtils.mkdir_p([SOURCE_DIR, DATA_DIR, DOCS_DIR])

raw = File.binread(INPUT)
utf8 = raw.dup.force_encoding("UTF-8")
unless utf8.valid_encoding?
  utf8 = raw.force_encoding("ISO-8859-1").encode("UTF-8")
end

raw_path = File.join(SOURCE_DIR, "agrolink-api-doc-specification.original.yaml")
yaml_path = File.join(SOURCE_DIR, "agrolink-api-doc-specification.yaml")
File.binwrite(raw_path, raw)
File.write(yaml_path, utf8, encoding: "UTF-8")

spec = Psych.safe_load(utf8, permitted_classes: [Date, Time], aliases: true)
raise "OpenAPI document is not a mapping" unless spec.is_a?(Hash)
raise "Missing openapi version" unless spec["openapi"]
raise "Missing paths" unless spec["paths"].is_a?(Hash)

HTTP_METHODS = %w[get post put patch delete head options trace].freeze

def ref_target(root, ref)
  return nil unless ref.is_a?(String) && ref.start_with?("#/")
  ref.delete_prefix("#/").split("/").reduce(root) do |memo, token|
    break nil unless memo.is_a?(Hash)
    memo[token.gsub("~1", "/").gsub("~0", "~")]
  end
end

def refs_in(value, found = [])
  case value
  when Hash
    found << value["$ref"] if value["$ref"]
    value.each_value { |child| refs_in(child, found) }
  when Array
    value.each { |child| refs_in(child, found) }
  end
  found
end

def frequency(values)
  values.each_with_object(Hash.new(0)) { |value, counts| counts[value] += 1 }.sort.to_h
end

def resolved(value, root)
  return value unless value.is_a?(Hash) && value["$ref"]
  target = ref_target(root, value["$ref"])
  target.is_a?(Hash) ? target.merge("x-source-ref" => value["$ref"]) : value
end

def schema_label(schema)
  return nil unless schema.is_a?(Hash)
  return schema["$ref"].split("/").last if schema["$ref"]
  return "array<#{schema_label(schema["items"]) || schema.dig("items", "type") || "unknown"}>" if schema["type"] == "array"
  schema["type"] || (schema["oneOf"] && "oneOf") || (schema["allOf"] && "allOf") || "object"
end

def content_map(container, root)
  return [] unless container.is_a?(Hash)
  (container["content"] || {}).map do |content_type, media|
    schema = media.is_a?(Hash) ? media["schema"] : nil
    { "contentType" => content_type, "schema" => schema_label(schema), "schemaRaw" => schema }
  end
end

def capability_for(method, path, text, response_types)
  corpus = "#{path} #{text}".downcase
  return "audit" if corpus.include?("audit")
  return "revert" if corpus.match?(/revert|undo|revers/)
  return "compare" if corpus.match?(/compare|compar|traceabilitycheck|ranking|staticscompare/)
  return "aggregate" if corpus.match?(/ranking|statistic|distribution|projection|cost|quotation|summary|resumen/)
  return "export" if corpus.match?(/report|informe|export|download/) || response_types.any? { |v| !v.include?("json") }
  return "import" if corpus.match?(/import|upload|filterbyfile|snig|caravanfile|attachment/) && method == "POST"
  return "delete" if method == "DELETE" || corpus.match?(/\/delete|baja/)
  return "batch" if corpus.match?(/batch|lote|assignments|updates|entries|exits|weighings|sanitaryapplications|split|merge/)
  return "update" if %w[PUT PATCH].include?(method)
  return "create" if method == "POST"
  return "search" if method == "GET" && !path.match?(/\{[^}]+\}/)
  "read"
end

def risk_for(method, capability, path, text)
  corpus = "#{path} #{text}".downcase
  return "R4" if method == "DELETE" || corpus.match?(/eliminaci[oó]n f[ií]sica/)
  return "R3" if %w[revert batch].include?(capability) || corpus.match?(/erpintegrat|changestate|revert|undo|masiv|\/delete/)
  return "R2" if %w[create update delete import].include?(capability) || %w[POST PUT PATCH].include?(method)
  return "R1" if capability == "export" || corpus.match?(/file|archivo|report|projection/)
  "R0"
end

def tool_candidate(tag, capability, path)
  domain = tag.to_s.downcase.gsub(/[^a-z0-9]+/, "_").gsub(/^_|_$/, "")
  domain = "api" if domain.empty?
  stem = path.split("/").reject(&:empty?).first.to_s.gsub(/[^a-zA-Z0-9]+/, "_").downcase
  case capability
  when "search" then "search_#{domain}"
  when "read" then "get_#{domain}_detail"
  when "aggregate" then "analyze_#{domain}"
  when "compare" then "compare_#{domain}"
  when "audit" then "get_#{domain}_audit"
  when "export" then "export_#{domain}"
  when "import" then "import_#{domain}"
  when "revert" then "revert_#{domain}_operation"
  when "batch" then "batch_#{domain}_operation"
  when "delete" then "delete_#{domain}_record"
  when "create" then "create_#{domain}_record"
  when "update" then "update_#{domain}_record"
  else "#{capability}_#{stem}"
  end
end

top_security = spec["security"] || []
operations = []

spec["paths"].each do |path, path_item|
  next unless path_item.is_a?(Hash)
  shared_parameters = Array(path_item["parameters"])
  path_item.each do |method_raw, operation|
    method = method_raw.to_s.downcase
    next unless HTTP_METHODS.include?(method)
    operation ||= {}
    method_up = method.upcase
    parameters = (shared_parameters + Array(operation["parameters"])).map do |param|
      source = resolved(param, spec)
      schema = source["schema"] || {}
      {
        "name" => source["name"],
        "in" => source["in"],
        "required" => !!source["required"],
        "description" => source["description"],
        "schema" => schema_label(schema),
        "schemaRaw" => schema,
        "ref" => param.is_a?(Hash) ? param["$ref"] : nil
      }
    end
    request_body = resolved(operation["requestBody"], spec)
    request_content = content_map(request_body, spec)
    responses = (operation["responses"] || {}).map do |status, response|
      source = resolved(response, spec)
      {
        "status" => status.to_s,
        "description" => source["description"],
        "content" => content_map(source, spec),
        "headers" => source["headers"] || {},
        "ref" => response.is_a?(Hash) ? response["$ref"] : nil
      }
    end
    response_types = responses.flat_map { |r| r["content"].map { |c| c["contentType"] } }.uniq
    tags = Array(operation["tags"])
    primary_tag = tags.first || "Untagged"
    text = [operation["summary"], operation["description"], operation["operationId"]].compact.join(" ")
    capability = capability_for(method_up, path, text, response_types)
    risk = risk_for(method_up, capability, path, text)
    operations << {
      "tag" => primary_tag,
      "tags" => tags,
      "method" => method_up,
      "path" => path,
      "operationId" => operation["operationId"],
      "summary" => operation["summary"],
      "description" => operation["description"],
      "deprecated" => !!operation["deprecated"],
      "parameters" => parameters,
      "requestBodyRequired" => request_body.is_a?(Hash) ? !!request_body["required"] : false,
      "requestContent" => request_content,
      "responses" => responses,
      "security" => operation.key?("security") ? operation["security"] : top_security,
      "capability" => capability,
      "risk" => risk,
      "toolCandidate" => tool_candidate(primary_tag, capability, path),
      "refs" => refs_in(operation).uniq
    }
  end
end

all_refs = refs_in(spec).uniq
unresolved_refs = all_refs.reject { |ref| ref_target(spec, ref) }

schemas = (spec.dig("components", "schemas") || {}).map do |name, schema|
  schema ||= {}
  properties = (schema["properties"] || {}).map do |property_name, property_schema|
    {
      "name" => property_name,
      "type" => schema_label(property_schema),
      "required" => Array(schema["required"]).include?(property_name),
      "nullable" => !!property_schema["nullable"],
      "readOnly" => !!property_schema["readOnly"],
      "writeOnly" => !!property_schema["writeOnly"],
      "description" => property_schema["description"],
      "enum" => property_schema["enum"],
      "format" => property_schema["format"],
      "ref" => property_schema["$ref"] || property_schema.dig("items", "$ref")
    }
  end
  {
    "name" => name,
    "type" => schema_label(schema),
    "description" => schema["description"],
    "required" => Array(schema["required"]),
    "properties" => properties,
    "enum" => schema["enum"],
    "refs" => refs_in(schema).uniq
  }
end

File.write(File.join(DATA_DIR, "openapi.json"), JSON.pretty_generate(spec) + "\n")
File.write(File.join(DATA_DIR, "endpoint-inventory.json"), JSON.pretty_generate(operations) + "\n")
File.write(File.join(DATA_DIR, "schema-catalog.json"), JSON.pretty_generate(schemas) + "\n")

CSV.open(File.join(DATA_DIR, "endpoint-inventory.csv"), "w", write_headers: true,
         headers: %w[tag method path operationId summary capability risk toolCandidate parameters requestContent responses security deprecated]) do |csv|
  operations.each do |op|
    csv << [
      op["tag"], op["method"], op["path"], op["operationId"], op["summary"], op["capability"], op["risk"],
      op["toolCandidate"],
      op["parameters"].map { |p| "#{p["in"]}:#{p["name"]}#{p["required"] ? "*" : ""}" }.join("; "),
      op["requestContent"].map { |c| "#{c["contentType"]}:#{c["schema"]}" }.join("; "),
      op["responses"].map { |r| "#{r["status"]}:#{r["content"].map { |c| c["schema"] }.compact.join("|")}" }.join("; "),
      JSON.generate(op["security"]), op["deprecated"]
    ]
  end
end

by_method = operations.group_by { |op| op["method"] }.transform_values(&:size).sort.to_h
by_tag = operations.group_by { |op| op["tag"] }.transform_values(&:size).sort.to_h
by_capability = operations.group_by { |op| op["capability"] }.transform_values(&:size).sort.to_h
by_risk = operations.group_by { |op| op["risk"] }.transform_values(&:size).sort.to_h
missing_operation_id = operations.select { |op| op["operationId"].to_s.empty? }
missing_summary = operations.select { |op| op["summary"].to_s.empty? }
missing_responses = operations.select { |op| op["responses"].empty? }
no_security = operations.select { |op| Array(op["security"]).empty? }
request_types = frequency(operations.flat_map { |op| op["requestContent"].map { |c| c["contentType"] } })
response_types = frequency(operations.flat_map { |op| op["responses"].flat_map { |r| r["content"].map { |c| c["contentType"] } } })
response_codes = frequency(operations.flat_map { |op| op["responses"].map { |r| r["status"] } })
parameter_locations = frequency(operations.flat_map { |op| op["parameters"].map { |p| p["in"] || "unknown" } })

summary = {
  "generatedAt" => Time.now.iso8601,
  "sourceSha256" => Digest::SHA256.hexdigest(raw),
  "openapi" => spec["openapi"],
  "apiVersion" => spec.dig("info", "version"),
  "title" => spec.dig("info", "title"),
  "servers" => spec["servers"] || [],
  "securitySchemes" => spec.dig("components", "securitySchemes") || {},
  "topLevelSecurity" => top_security,
  "pathCount" => spec["paths"].size,
  "operationCount" => operations.size,
  "schemaCount" => schemas.size,
  "refCount" => all_refs.size,
  "unresolvedRefs" => unresolved_refs,
  "byMethod" => by_method,
  "byTag" => by_tag,
  "byCapability" => by_capability,
  "byRisk" => by_risk,
  "parameterLocations" => parameter_locations,
  "requestContentTypes" => request_types,
  "responseContentTypes" => response_types,
  "responseCodes" => response_codes,
  "quality" => {
    "missingOperationId" => missing_operation_id.map { |op| "#{op["method"]} #{op["path"]}" },
    "missingSummary" => missing_summary.map { |op| "#{op["method"]} #{op["path"]}" },
    "missingResponses" => missing_responses.map { |op| "#{op["method"]} #{op["path"]}" },
    "operationsWithoutSecurity" => no_security.map { |op| "#{op["method"]} #{op["path"]}" }
  }
}
File.write(File.join(DATA_DIR, "extraction-summary.json"), JSON.pretty_generate(summary) + "\n")

details = []
details << "# Inventario detallado de endpoints"
details << ""
details << "Fuente: OpenAPI #{spec["openapi"]}, API #{spec.dig("info", "version")}. Inventario generado desde el contrato canónico normalizado a UTF-8."
details << ""
operations.group_by { |op| op["tag"] }.sort.each do |tag, tag_ops|
  details << "## #{tag}"
  details << ""
  details << "| Método | Ruta | `operationId` | Capacidad | Riesgo | Entrada | Respuestas | Tool candidata |"
  details << "|---|---|---|---|---|---|---|---|"
  tag_ops.each do |op|
    input = []
    input.concat(op["parameters"].map { |p| "#{p["in"]}:#{p["name"]}#{p["required"] ? "*" : ""}" })
    input.concat(op["requestContent"].map { |c| "#{c["contentType"]}→#{c["schema"]}" })
    responses = op["responses"].map { |r| r["status"] }.join(", ")
    cells = [op["method"], "`#{op["path"]}`", "`#{op["operationId"]}`", op["capability"], op["risk"], input.join("<br>"), responses, "`#{op["toolCandidate"]}`"]
    details << "| #{cells.map { |c| c.to_s.gsub("|", "\\|") }.join(" | ")} |"
  end
  details << ""
end
File.write(File.join(DOCS_DIR, "03-inventario-detallado.md"), details.join("\n") + "\n")

technical = []
technical << "# Mapa técnico de la API del cliente de Solvo"
technical << ""
technical << "## Resumen de cobertura"
technical << ""
technical << "- Rutas: **#{summary["pathCount"]}**."
technical << "- Operaciones: **#{summary["operationCount"]}**."
technical << "- Schemas: **#{summary["schemaCount"]}**."
technical << "- Referencias únicas: **#{summary["refCount"]}**."
technical << "- Referencias sin resolver: **#{unresolved_refs.size}**."
technical << "- SHA-256 de la fuente: `#{summary["sourceSha256"]}`."
technical << ""
technical << "## Autenticación"
technical << ""
technical << "```json"
technical << JSON.pretty_generate(summary["securitySchemes"])
technical << "```"
technical << ""
technical << "Seguridad global: `#{JSON.generate(top_security)}`. El agente debe propagar el token del usuario al cliente de Solvo y nunca tratar el historial conversacional como autorización."
technical << ""
technical << "## Distribución por capacidad"
technical << ""
technical << "| Capacidad | Operaciones |"
technical << "|---|---:|"
by_capability.each { |name, count| technical << "| #{name} | #{count} |" }
technical << ""
technical << "## Distribución por riesgo"
technical << ""
technical << "| Riesgo | Operaciones |"
technical << "|---|---:|"
by_risk.each { |name, count| technical << "| #{name} | #{count} |" }
technical << ""
technical << "## Tipos de contenido"
technical << ""
technical << "### Solicitudes"
technical << ""
request_types.each { |name, count| technical << "- `#{name}`: #{count}." }
technical << ""
technical << "### Respuestas"
technical << ""
response_types.each { |name, count| technical << "- `#{name}`: #{count}." }
technical << ""
technical << "## Calidad del contrato"
technical << ""
technical << "- Operaciones sin `operationId`: #{missing_operation_id.size}."
technical << "- Operaciones sin `summary`: #{missing_summary.size}."
technical << "- Operaciones sin respuestas: #{missing_responses.size}."
technical << "- Operaciones sin seguridad efectiva: #{no_security.size}."
technical << "- Referencias sin resolver: #{unresolved_refs.size}."
technical << ""
technical << "## Archivos generados"
technical << ""
technical << "- `data/endpoint-inventory.json`: contratos normalizados por operación."
technical << "- `data/endpoint-inventory.csv`: vista tabular para revisión."
technical << "- `data/schema-catalog.json`: catálogo de modelos y relaciones."
technical << "- `data/extraction-summary.json`: métricas y controles de calidad."
technical << "- `data/openapi.json`: representación JSON del contrato completo."
File.write(File.join(DOCS_DIR, "04-mapa-tecnico.md"), technical.join("\n") + "\n")

questions = []
questions << "# Preguntas y decisiones pendientes para el cliente de Solvo"
questions << ""
questions << "## Bloqueantes de integración"
questions << ""
questions << "1. El único servidor declarado es `#{spec.dig("servers", 0, "url")}`. Se necesitan las URLs reales de desarrollo, pruebas y producción."
questions << "2. Confirmar cómo se obtiene, valida y renueva el token `bearerAuth`, y qué claims identifican usuario, roles y establecimientos."
questions << "3. Confirmar si todos los endpoints heredan la seguridad global o existen permisos adicionales no expresados en OpenAPI."
questions << "4. Definir límites de paginación, timeouts, rate limits y tamaño máximo de respuestas y archivos."
questions << "5. Proporcionar usuarios de prueba con perfiles representativos y datos no sensibles."
questions << "6. Confirmar los valores máximos y predeterminados de `skip` y `take`; el contrato los utiliza en 20 operaciones pero no documenta límites."
questions << ""
questions << "## Decisiones funcionales"
questions << ""
questions << "1. Confirmar qué módulos forman parte del MVP conversacional."
questions << "2. Confirmar si eliminaciones físicas, reversión, cambios de estado e integraciones ERP deben quedar completamente fuera del agente inicial."
questions << "3. Definir qué operaciones requieren confirmación simple, confirmación reforzada o doble aprobación."
questions << "4. Aclarar la diferencia entre los tags `Supply Settlement` y `Supply Settlements`."
questions << "5. Aclarar por qué `Position Reports` está declarado sin operaciones."
questions << "6. Definir qué entidad es la fuente oficial para resolver establecimientos, productores, categorías, consignatarios e intermediarios."
questions << "7. Confirmar qué cálculos deben ejecutarse en el cliente de Solvo y cuáles pueden realizarse sobre resultados devueltos por la API."
questions << ""
questions << "## Calidad documental detectada"
questions << ""
questions << "- Operaciones sin `operationId`: #{missing_operation_id.size}."
questions << "- Operaciones sin resumen: #{missing_summary.size}."
questions << "- Operaciones sin seguridad efectiva: #{no_security.size}."
questions << "- Referencias sin resolver: #{unresolved_refs.size}."
questions << "- Dos operaciones protegidas por seguridad global no documentan respuesta `401`: `PATCH /livestock/{id}/caravan` y `PUT /supplyreceivings/{id}/lines`."
questions << "- Solo 28 de 214 operaciones documentan una respuesta `500`; confirmar si existe un contrato común de error no reflejado en OpenAPI."
questions << "- La presencia de `403`, `404` y `409` es desigual entre operaciones similares; revisar consistencia del catálogo de errores."
unless unresolved_refs.empty?
  questions << ""
  questions << "Referencias sin resolver:"
  unresolved_refs.each { |ref| questions << "- `#{ref}`" }
end
File.write(File.join(DOCS_DIR, "05-preguntas-para-cliente-solvo.md"), questions.join("\n") + "\n")

schema_doc = []
schema_doc << "# Catálogo de schemas"
schema_doc << ""
schema_doc << "El contrato declara **#{schemas.size} schemas**. La tabla permite ubicar modelos complejos, dependencias y enums antes de diseñar los contratos reducidos de cada tool."
schema_doc << ""
schema_doc << "| Schema | Tipo | Propiedades | Requeridas | Referencias |"
schema_doc << "|---|---|---:|---:|---|"
schemas.sort_by { |schema| schema["name"] }.each do |schema|
  refs = schema["refs"].map { |ref| ref.split("/").last }.uniq.join(", ")
  schema_doc << "| `#{schema["name"]}` | #{schema["type"]} | #{schema["properties"].size} | #{schema["required"].size} | #{refs} |"
end
schema_doc << ""
schema_doc << "## Reglas de uso"
schema_doc << ""
schema_doc << "- Los DTO grandes no se exponen completos al modelo de lenguaje."
schema_doc << "- La capa de adaptación selecciona campos por intención y completa valores técnicos."
schema_doc << "- Los enums se resuelven a valores válidos antes de llamar a la API."
schema_doc << "- Los campos `readOnly` no forman parte de entradas y los `writeOnly` no se muestran en respuestas."
schema_doc << "- Los schemas completos y propiedades están disponibles en `data/schema-catalog.json`."
File.write(File.join(DOCS_DIR, "08-catalogo-de-schemas.md"), schema_doc.join("\n") + "\n")

risk_doc = []
risk_doc << "# Matriz de riesgo y controles"
risk_doc << ""
risk_doc << "## Distribución"
risk_doc << ""
risk_doc << "| Nivel | Operaciones | Control mínimo |"
risk_doc << "|---|---:|---|"
risk_doc << "| R0 | #{by_risk.fetch("R0", 0)} | Permisos de API, límites y trazabilidad |"
risk_doc << "| R1 | #{by_risk.fetch("R1", 0)} | Aviso de procesamiento, límites de archivo y expiración |"
risk_doc << "| R2 | #{by_risk.fetch("R2", 0)} | Validación, lectura previa y resumen antes de ejecutar |"
risk_doc << "| R3 | #{by_risk.fetch("R3", 0)} | Confirmación explícita, idempotencia y auditoría reforzada |"
risk_doc << "| R4 | #{by_risk.fetch("R4", 0)} | Excluir del MVP o aplicar aprobación reforzada |"
risk_doc << ""
risk_doc << "## Controles transversales"
risk_doc << ""
risk_doc << "1. Propagar el JWT del usuario sin incluirlo en prompts, logs o memoria conversacional."
risk_doc << "2. Resolver y validar establecimientos dentro del alcance autorizado."
risk_doc << "3. Aplicar límites predeterminados a `skip` y `take`."
risk_doc << "4. Registrar tool, endpoint, usuario, parámetros no sensibles, resultado y duración."
risk_doc << "5. No reintentar automáticamente mutaciones sin una clave de idempotencia o confirmación de estado."
risk_doc << "6. Verificar estado actual antes de cambios de estado, ediciones sensibles y reversión."
risk_doc << "7. Analizar tipo, tamaño y contenido permitido antes de aceptar archivos."
risk_doc << "8. Traducir `401`, `403`, `404`, `409` y errores de validación a mensajes sin detalles internos."
risk_doc << ""
risk_doc << "## Operaciones R4"
risk_doc << ""
operations.select { |op| op["risk"] == "R4" }.each do |op|
  risk_doc << "- `#{op["method"]} #{op["path"]}` — #{op["summary"]}"
end
File.write(File.join(DOCS_DIR, "09-matriz-de-riesgo-y-controles.md"), risk_doc.join("\n") + "\n")

puts JSON.pretty_generate(summary)
