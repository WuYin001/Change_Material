bl_info = {
    "name": "Node Group Input Copy/Paste",
    "description": "Remember and apply node group input socket data for Compositor and Geometry nodes.",
    "author": "Jules",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "Node Editor > Sidebar > Group Copy",
    "category": "Node",
}

import bpy

# Global dictionary to store data separately for each tree type
# Keys will be 'CompositorNodeTree' and 'GeometryNodeTree'
node_group_data_storage = {
    'CompositorNodeTree': None,
    'GeometryNodeTree': None,
    'ShaderNodeTree': None # Added for robustness, though focus is on the other two
}

def serialize_value(val):
    """Convert Blender socket values (like mathutils.Vector) to serializable types."""
    if hasattr(val, "to_list"):
        return val.to_list()
    if isinstance(val, (int, float, str, bool)):
        return val
    if hasattr(val, "__iter__"):
        return list(val)
    return val

class NODE_OT_remember_group_data(bpy.types.Operator):
    """Remember the input values of the selected node group"""
    bl_idname = "node.remember_group_data"
    bl_label = "Remember Node Group Inputs"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_node and context.active_node.type == 'GROUP'

    def execute(self, context):
        node = context.active_node
        tree_type = context.space_data.tree_type

        if tree_type not in node_group_data_storage:
            # We allow unknown tree types but warn the user.
            self.report({'WARNING'}, f"Tree type {tree_type} not explicitly supported, but data will be stored.")
            node_group_data_storage[tree_type] = None

        data = []
        for input in node.inputs:
            if hasattr(input, 'default_value'):
                data.append({
                    'identifier': input.identifier,
                    'name': input.name,
                    'value': serialize_value(input.default_value)
                })

        node_group_data_storage[tree_type] = {
            'node_name': node.name,
            'node_tree_name': node.node_tree.name if node.node_tree else "Unknown",
            'inputs': data
        }

        self.report({'INFO'}, f"Remembered {len(data)} inputs for {tree_type}")
        return {'FINISHED'}

class NODE_OT_apply_group_data(bpy.types.Operator):
    """Apply the remembered input values to the selected node group"""
    bl_idname = "node.apply_group_data"
    bl_label = "Apply Node Group Inputs"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        tree_type = context.space_data.tree_type
        return (context.active_node and
                context.active_node.type == 'GROUP' and
                node_group_data_storage.get(tree_type) is not None)

    def execute(self, context):
        node = context.active_node
        tree_type = context.space_data.tree_type
        storage = node_group_data_storage.get(tree_type)

        if not storage:
            self.report({'WARNING'}, "No data remembered for this tree type")
            return {'CANCELLED'}

        data = storage['inputs']

        # Create mappings for matching
        id_map = {item['identifier']: item['value'] for item in data}
        name_map = {item['name']: item['value'] for item in data}

        count = 0
        for input in node.inputs:
            if not hasattr(input, 'default_value'):
                continue

            val = None
            # Try matching by identifier first (more accurate for the same group)
            if input.identifier in id_map:
                val = id_map[input.identifier]
            # Then by name (useful when applying to a similar group)
            elif input.name in name_map:
                val = name_map[input.name]

            if val is not None:
                try:
                    input.default_value = val
                    count += 1
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to apply value to {input.name}: {e}")

        self.report({'INFO'}, f"Applied {count} inputs from remembered group '{storage['node_tree_name']}'")
        return {'FINISHED'}

class NODE_PT_group_copy_paste(bpy.types.Panel):
    """Creates a Panel in the Node Editor Sidebar"""
    bl_label = "Node Group Copy/Paste"
    bl_idname = "NODE_PT_group_copy_paste"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Group Copy'

    def draw(self, context):
        layout = self.layout
        tree_type = context.space_data.tree_type
        storage = node_group_data_storage.get(tree_type)

        col = layout.column(align=True)
        col.operator("node.remember_group_data", icon='COPY_ID', text="Remember Inputs")

        row = col.row(align=True)
        row.operator("node.apply_group_data", icon='PASTE_ID', text="Apply Inputs")

        # Disable Apply button if no data is remembered for this tree type
        if not storage:
            row.enabled = False

        if storage:
            box = layout.box()
            box.label(text=f"Stored: {storage['node_tree_name']}", icon='NODETREE')
            box.label(text=f"Inputs: {len(storage['inputs'])}")

classes = (
    NODE_OT_remember_group_data,
    NODE_OT_apply_group_data,
    NODE_PT_group_copy_paste,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
