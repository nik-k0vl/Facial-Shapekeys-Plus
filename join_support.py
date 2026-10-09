import bpy


_keymaps = []


def draw_join(self, context):
    if context.object and context.object.type == 'MESH':
        self.layout.operator('object.skp_join')


def register():
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig:
        keymap = keyconfig.keymaps.new(name='Object Mode', space_type='EMPTY')
        item = keymap.keymap_items.new('object.skp_join', 'J', 'PRESS', ctrl=True)
        _keymaps.append((keymap, item))

    bpy.types.VIEW3D_MT_object.append(draw_join)
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_join)


def unregister():
    for keymap, item in _keymaps:
        keymap.keymap_items.remove(item)
    _keymaps.clear()

    bpy.types.VIEW3D_MT_object.remove(draw_join)
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_join)
