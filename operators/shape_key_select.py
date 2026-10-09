import bpy

from .. import core


class OBJECT_OT_skp_shape_key_select(bpy.types.Operator):
    bl_idname = 'object.skp_shape_key_select'
    bl_label = core.strings['operators.ShapeKeySelect.bl_label']
    bl_description = core.strings['operators.ShapeKeySelect.bl_description']
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: bpy.props.EnumProperty(
        items=(
            ('TOGGLE', "", ""),
            ('RANGE', "", ""),
            ('ALL', "", ""),
            ('NONE', "", ""),
            ('INVERSE', "", "")
        ),
        options={'HIDDEN', 'SKIP_SAVE'})
    
    index: bpy.props.IntProperty(options={'HIDDEN', 'SKIP_SAVE'})
    range_start: bpy.props.IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})
    
    @classmethod
    def poll(cls, context):
        return context.object and context.object.data.shape_keys
    
    def invoke(self, context, event):
        if self.mode != 'TOGGLE':
            return self.execute(context)
        
        obj = context.object
        key_props = obj.data.shape_keys.shape_keys_plus
        key_blocks = obj.data.shape_keys.key_blocks
        if not 0 < self.index < len(key_blocks):
            return {'CANCELLED'}

        # Resolve by name so moving keys does not move the selection's starting point.
        # The index fallback supports anchors saved by previous add-on versions.
        anchor = (key_blocks.find(key_props.select_anchor_name) if key_props.select_anchor_name
                  else key_props.select_anchor)
        if not 0 < anchor < len(key_blocks) or not core.key.get_selected_indices():
            anchor = self.index

        if event.shift:
            self.mode = 'RANGE'
            self.range_start = anchor
            return self.execute(context)

        if event.ctrl:
            selected = set(core.key.get_selected_indices())

            if self.index in selected:
                core.key.select(self.index, False)
            else:
                core.key.select(anchor, True)
                core.key.select(self.index, True)

            key_props.select_anchor = self.index
            key_props.select_anchor_name = key_blocks[self.index].name
            if not core.key.get_selected_indices():
                key_props.select_anchor = -1
                key_props.select_anchor_name = ""
            obj.active_shape_key_index = self.index
            return {'FINISHED'}

        return self.execute(context)
    
    def execute(self, context):
        obj = context.object
        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks
        key_props = shape_keys.shape_keys_plus
        selections = key_props.selections
        
        if self.mode == 'TOGGLE':
            if not 0 < self.index < len(key_blocks):
                return {'CANCELLED'}
            core.key.select(self.index, str(self.index) not in selections)
            key_props.select_anchor = self.index
            key_props.select_anchor_name = key_blocks[self.index].name
        elif self.mode == 'RANGE':
            if not (0 < self.index < len(key_blocks) and 0 < self.range_start < len(key_blocks)):
                return {'CANCELLED'}
            start, end = sorted((self.range_start, self.index))
            for index in range(start, end + 1):
                core.key.select(index, True)
            # Further Shift-clicks extend from the original checkbox, not the last endpoint.
            key_props.select_anchor = self.range_start
            key_props.select_anchor_name = key_blocks[self.range_start].name
            obj.active_shape_key_index = self.index
        elif self.mode == 'ALL':
            for index, key in enumerate(key_blocks):
                if str(index) not in selections:
                    core.key.select(index, True)
        elif self.mode == 'NONE':
            selections.clear()
        elif self.mode == 'INVERSE':
            for index, key in enumerate(key_blocks):
                core.key.select(index, str(index) not in selections)

        if self.mode in {'ALL', 'NONE', 'INVERSE'} or not core.key.get_selected_indices():
            key_props.select_anchor = -1
            key_props.select_anchor_name = ""
        
        return {'FINISHED'}
