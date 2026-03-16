require 'json'
require 'yaml'

module Atelier
  class WorkflowObserver < Sketchup::ModelObserver

    def initialize(output_path)
      @output_path  = output_path
      @linear_flow  = []
      @undo_log     = []
      @undo_stack   = []   # temp stack, collects consecutive undos
      @last_state   = nil  # output of last committed operation
      @recording    = false
    end

    # ------------------------------------------------------------------
    # Public controls
    # ------------------------------------------------------------------

    def start(model)
      @recording   = true
      @last_state  = capture_state(model)
      @s0          = capture_s0(model)
      puts "[Atelier] Recording started."
    end

    def stop(model)
      @recording = false
      write_yaml
      puts "[Atelier] Recording stopped. Saved to #{@output_path}"
    end

    # ------------------------------------------------------------------
    # ModelObserver callbacks
    # ------------------------------------------------------------------

    def onTransactionCommit(model)
      return unless @recording

      # flush any pending undos into undo_log before appending new delta
      flush_undo_stack

      current_state = capture_state(model)
      op_name       = get_operation_name(model)

      delta = {
        "index"     => @linear_flow.length,
        "timestamp" => Time.now.to_i,
        "operation" => op_name,
        "context"   => { "active_path" => get_active_path(model) },
        "input"     => @last_state,
        "output"    => current_state
      }

      @linear_flow << delta
      @undo_log    << []            # empty slot for this index
      @last_state   = current_state
    end

    def onTransactionUndo(model)
      return unless @recording
      return if @linear_flow.empty?

      undone      = @linear_flow.pop
      @undo_log.pop
      @undo_stack << undone         # collect in stack order (will reverse on flush)
      @last_state = @linear_flow.last&.dig("output")
    end

    def onTransactionRedo(model)
      # redo triggers onTransactionCommit automatically, nothing extra needed
    end

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    private

    def flush_undo_stack
      return if @undo_stack.empty?
      # reverse to restore original execution order (B semantics)
      abandoned = @undo_stack.reverse
      @undo_stack = []
      # attach to the slot just before the next linear_flow entry
      idx = @linear_flow.length
      @undo_log[idx] = abandoned
    end

    def get_operation_name(model)
      # SketchUp surfaces the last operation name via the undo stack description
      model.respond_to?(:undo_manager) ? model.undo_manager.last_operation_name : "unknown"
    end

    def get_active_path(model)
      path = model.active_path
      return [] if path.nil? || path.empty?
      path.map { |e| entity_id(e) }
    end

    def capture_state(model)
      sel = model.selection
      return nil if sel.empty?
      entity = sel.first
      {
        "entity_id"   => entity_id(entity),
        "entity_type" => entity.typename,
        "position"    => entity_position(entity),
        "parameters"  => {}
      }
    end

    def capture_s0(model)
      entities  = {}
      materials = {}

      # root node
      entities["root"] = {
        "type"     => "Model",
        "parent"   => nil,
        "children" => model.entities.map { |e| entity_id(e) }
      }

      # walk all entities recursively
      walk_entities(model.entities, "root", entities)

      # materials
      model.materials.each do |mat|
        color = mat.color
        materials[mat.name] = {
          "color"   => [color.red, color.green, color.blue],
          "texture" => mat.texture&.filename
        }
      end

      {
        "timestamp"   => Time.now.to_i,
        "model_units" => units_string(model),
        "entities"    => entities,
        "materials"   => materials
      }
    end

    def walk_entities(entities, parent_id, acc)
      entities.each do |e|
        id = entity_id(e)
        case e
        when Sketchup::Group
          acc[id] = {
            "type"      => "Group",
            "parent"    => parent_id,
            "transform" => e.transformation.to_a,
            "children"  => e.entities.map { |c| entity_id(c) }
          }
          walk_entities(e.entities, id, acc)
        when Sketchup::ComponentInstance
          acc[id] = {
            "type"       => "Component",
            "parent"     => parent_id,
            "definition" => e.definition.name,
            "transform"  => e.transformation.to_a,
            "children"   => e.definition.entities.map { |c| entity_id(c) }
          }
          walk_entities(e.definition.entities, id, acc)
        when Sketchup::Face
          acc[id] = {
            "type"     => "Face",
            "parent"   => parent_id,
            "vertices" => e.vertices.map { |v| v.position.to_a },
            "normal"   => e.normal.to_a,
            "material" => e.material&.name
          }
        when Sketchup::Edge
          acc[id] = {
            "type"   => "Edge",
            "parent" => parent_id,
            "start"  => e.start.position.to_a,
            "end"    => e.end.position.to_a
          }
        end
      end
    end

    def entity_id(entity)
      "#{entity.typename.downcase}_#{entity.entityID}"
    end

    def entity_position(entity)
      case entity
      when Sketchup::Group, Sketchup::ComponentInstance
        entity.transformation.origin.to_a
      when Sketchup::Face
        entity.bounds.center.to_a
      when Sketchup::Edge
        entity.start.position.to_a
      else
        [0.0, 0.0, 0.0]
      end
    end

    def units_string(model)
      case model.options["UnitsOptions"]["LengthUnit"]
      when 0 then "inch"
      when 1 then "feet"
      when 2 then "mm"
      when 3 then "cm"
      when 4 then "m"
      else "mm"
      end
    end

    def write_yaml
      data = {
        "s0"          => @s0,
        "linear_flow" => @linear_flow,
        "undo_log"    => @undo_log
      }
      File.write(@output_path, data.to_yaml)
    end

  end
end