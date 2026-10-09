import bpy

from .. import core
from .. import memory


class OBJECT_OT_skp_shape_key_sort(bpy.types.Operator):
    bl_idname = 'object.skp_shape_key_sort'
    bl_label = core.strings['operators.ShapeKeySort.bl_label']
    bl_description = core.strings['operators.ShapeKeySort.bl_description']
    bl_options = {'REGISTER', 'UNDO'}

    order: bpy.props.EnumProperty(
        name=core.strings['operators.ShapeKeySort.order.name'],
        items=(
            ('ASCENDING', core.strings['operators.ShapeKeySort.order.items[ASCENDING].name'], ""),
            ('DESCENDING', core.strings['operators.ShapeKeySort.order.items[DESCENDING].name'], ""),
        ),
        default='ASCENDING')

    @classmethod
    def poll(cls, context):
        obj = context.object
        shape_keys = getattr(getattr(obj, 'data', None), 'shape_keys', None)
        if not shape_keys or obj.mode == 'EDIT':
            return False

        indices = core.key.get_selected_indices()
        return (len({index for index in indices if 0 < index < len(shape_keys.key_blocks)}) > 1
                and bpy.ops.object.shape_key_move.poll())

    def execute(self, context):
        obj = context.object
        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks
        key_props = shape_keys.shape_keys_plus
        selections = [key_blocks[index].name for index in core.key.get_selected_indices()
                      if 0 < index < len(key_blocks)]
        if len(set(selections)) < 2:
            return {'CANCELLED'}

        tree = memory.tree()
        original_order = list(tree.get_flattened())
        tree.sort_selected(selections, reverse=self.order == 'DESCENDING')
        if tree.get_flattened() == original_order:
            return {'FINISHED'}

        active_name = obj.active_shape_key.name
        anchor_name = key_props.select_anchor_name
        if not anchor_name and 0 < key_props.select_anchor < len(key_blocks):
            anchor_name = key_blocks[key_props.select_anchor].name
        hidden = core.utils.hide(obj)

        try:
            key_props.selections.clear()
            tree.apply()
        finally:
            # Selections and the active key refer to identities, not their old row indices.
            core.key.reselect(selections)
            obj.active_shape_key_index = key_blocks.find(active_name)
            key_props.select_anchor_name = anchor_name if anchor_name in key_blocks else ""
            key_props.select_anchor = key_blocks.find(anchor_name) if anchor_name else -1
            core.utils.show(hidden)

        memory.changed()
        return {'FINISHED'}
