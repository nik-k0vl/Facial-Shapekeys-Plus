import bpy

from .. import core
from .. import memory


class OBJECT_OT_skp_join(bpy.types.Operator):
    bl_idname = 'object.skp_join'
    bl_label = core.strings['operators.Join.bl_label']
    bl_description = core.strings['operators.Join.bl_description']
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.ops.object.join.poll()

    def execute(self, context):
        obj = context.object
        meshes = [other for other in context.selected_editable_objects if other.type == 'MESH']

        # Curves and other supported object types retain Blender's usual join.
        if obj.type != 'MESH' or len(meshes) < 2:
            return bpy.ops.object.join()

        snapshots = []
        has_folders = False

        # Source objects cease to exist during the native join. Capture their trees
        # and metadata now, without retaining references to their shape keys.
        for other in [obj] + [other for other in meshes if other != obj]:
            shape_keys = other.data.shape_keys
            if shape_keys:
                tree = memory.tree(other)
                metadata = {key.name: key.vertex_group for key in shape_keys.key_blocks}
                snapshots.append((tree.tree, metadata))
                has_folders |= any(core.key.is_folder(key) for key in shape_keys.key_blocks)

        if not has_folders:
            return bpy.ops.object.join()

        active_name = getattr(obj.active_shape_key, 'name', None)
        selections = [key.name for key in core.key.get_selected()]
        result = bpy.ops.object.join()

        if 'FINISHED' not in result or not obj.data.shape_keys:
            return result

        key_blocks = obj.data.shape_keys.key_blocks
        branch, metadata = core.join.merge_hierarchies(snapshots, list(key_blocks.keys()))
        hidden = core.utils.hide(obj)

        try:
            obj.data.shape_keys.shape_keys_plus.selections.clear()
            for name, vertex_group in metadata.items():
                key_blocks[name].vertex_group = vertex_group

            # Do not reconstruct a tree from the joined list: its old child counts
            # no longer describe that list. Apply the captured, merged tree directly.
            tree = memory.tree(tree=branch)
            tree.apply()

            if active_name and active_name in key_blocks:
                obj.active_shape_key_index = key_blocks.find(active_name)
            else:
                obj.active_shape_key_index = 0
            core.key.reselect(selections)
        finally:
            core.utils.show(hidden)

        memory.changed()
        return {'FINISHED'}
