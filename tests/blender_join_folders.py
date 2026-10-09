"""Run with blender --background --factory-startup --python tests/blender_join_folders.py."""
import importlib.util
from pathlib import Path
import runpy
import sys
import unittest

import bpy
from bl_keymap_utils.io import keyconfig_init_from_data


# Background Blender has empty default keymaps. Load the standard map so that
# this test checks precedence over native Ctrl+J as well as shortcut registration.
defaults = runpy.run_path(str(Path(bpy.utils.system_resource('SCRIPTS')) /
                             'presets' / 'keyconfig' / 'keymap_data' / 'blender_default.py'))
keyconfig_init_from_data(bpy.context.window_manager.keyconfigs.default,
                        defaults['generate_keymaps'](defaults['Params']()))


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'facial_shapekeys_plus_test'
spec = importlib.util.spec_from_file_location(
    PACKAGE, ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
addon = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE] = addon
spec.loader.exec_module(addon)
bpy.context.preferences.addons.new().module = PACKAGE
addon.register()


class JoinFolderTests(unittest.TestCase):
    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        addon.memory.frame = {}
        addon.memory.tree.active = None

    def mesh(self, name, tree=None, settings=None):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        if tree is None:
            return obj

        def add(branch):
            for item in branch:
                folder = isinstance(item, list)
                name = item[0] if folder else item
                key = obj.shape_key_add(name=name, from_mix=False)
                if folder:
                    options = (settings or {}).get(name, {})
                    key.vertex_group = addon.core.folder.generate(children=len(item) - 1, **options)
                    add(item[1:])

        add(tree)
        return obj

    def select(self, active, *others):
        bpy.context.view_layer.update()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(False)
        for obj in (active,) + others:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active

    def join(self, active, *others):
        self.select(active, *others)
        self.assertEqual(bpy.ops.object.skp_join(), {'FINISHED'})
        return active

    def assert_tree(self, obj, expected):
        self.assertEqual(addon.memory.tree(obj).tree, expected)
        self.assertEqual(list(obj.data.shape_keys.key_blocks.keys()), addon.core.utils.flatten(expected))

    def test_original_cube_sphere_case(self):
        cube = self.mesh('Cube', ['Basis', ['Folder_1', 'shapekey_1', 'shapekey_2']])
        sphere = self.mesh('Sphere', ['Basis', ['Folder_1', 'shapekey_3', 'shapekey_4']])
        self.join(cube, sphere)
        self.assert_tree(cube, ['Basis', ['Folder_1', 'shapekey_1', 'shapekey_2', 'shapekey_3', 'shapekey_4']])
        self.assertEqual(len(cube.data.vertices), 6)
        self.assertEqual(len(bpy.data.objects), 1)

    def test_active_mesh_can_be_sphere(self):
        cube = self.mesh('Cube', ['Basis', ['Folder_1', 'shapekey_1', 'shapekey_2']])
        sphere = self.mesh('Sphere', ['Basis', ['Folder_1', 'shapekey_3', 'shapekey_4']])
        self.join(sphere, cube)
        self.assert_tree(sphere, ['Basis', ['Folder_1', 'shapekey_3', 'shapekey_4', 'shapekey_1', 'shapekey_2']])

    def test_three_meshes_multiple_nested_folders(self):
        a = self.mesh('A', ['Basis', ['Face', ['Eyes', 'a_eye'], ['Mouth', 'a_mouth']], 'loose_a'])
        b = self.mesh('B', ['Basis', ['Face', ['Eyes', 'b_eye'], ['Mouth', 'b_mouth']]])
        c = self.mesh('C', ['Basis', ['Face', ['Eyes', 'c_eye'], ['Brows', 'c_brow']], ['Unique', 'c_unique']])
        self.join(a, b, c)
        self.assert_tree(a, ['Basis', ['Face', ['Eyes', 'a_eye', 'b_eye', 'c_eye'],
                                     ['Mouth', 'a_mouth', 'b_mouth'], ['Brows', 'c_brow']],
                             'loose_a', ['Unique', 'c_unique']])
        keys = a.data.shape_keys.key_blocks
        self.assertEqual(addon.core.folder.get_block_value(keys['Face'], 'children'), 3)
        self.assertEqual(addon.core.folder.get_capacity(keys['Face']), 9)

    def test_unique_source_folders_and_root_keys(self):
        a = self.mesh('A', ['Basis', ['Active', 'a'], 'loose_a'])
        b = self.mesh('B', ['Basis', ['Source', ['Nested', 'b']], 'loose_b'])
        self.join(a, b)
        self.assert_tree(a, ['Basis', ['Active', 'a'], 'loose_a', ['Source', ['Nested', 'b']], 'loose_b'])

    def test_exact_names_only_and_empty_folders(self):
        a = self.mesh('A', ['Basis', ['Folder_1'], ['Empty']])
        b = self.mesh('B', ['Basis', ['Folder_1', 'b'], ['Folder_1.001', 'different'], ['Empty']])
        self.join(a, b)
        self.assert_tree(a, ['Basis', ['Folder_1', 'b'], ['Empty'], ['Folder_1.001', 'different']])

    def test_folder_settings_active_key_and_selection_survive(self):
        a = self.mesh('A', ['Basis', ['Folder', 'a']], {'Folder': {'expand': 0, 'icons': -8}})
        b = self.mesh('B', ['Basis', ['Folder', 'b']], {'Folder': {'expand': 1, 'icons': 2}})
        self.select(a, b)
        a.active_shape_key_index = 2
        addon.core.key.select('a', True)
        self.assertEqual(bpy.ops.object.skp_join(), {'FINISHED'})
        self.assertEqual(a.active_shape_key.name, 'a')
        self.assertEqual([key.name for key in addon.core.key.get_selected()], ['a'])
        self.assertEqual(a.data.shape_keys.key_blocks['Folder'].vertex_group, 'SKP.C2.E0.I-8')
        self.assertEqual(addon.memory.tree.active.tree, ['Basis', ['Folder', 'a', 'b']])
        self.assertFalse(a.hide_viewport)
        self.assertTrue(a.select_get())

    def test_active_parent_wins_for_shared_keys_and_folders(self):
        a = self.mesh('A', ['Basis', ['A_parent', ['Shared', 'shared_key']], 'loose_shared'])
        b = self.mesh('B', ['Basis', ['B_parent', ['Shared', 'shared_key', 'new'], 'loose_shared']])
        self.join(a, b)
        self.assert_tree(a, ['Basis', ['A_parent', ['Shared', 'shared_key', 'new']],
                             'loose_shared', ['B_parent']])

    def test_normal_key_folder_name_collision_preserves_active_type(self):
        a = self.mesh('A', ['Basis', 'Same_name'])
        a.data.shape_keys.key_blocks['Same_name'].vertex_group = 'Real vertex group'
        b = self.mesh('B', ['Basis', ['Same_name', 'b']])
        self.join(a, b)
        self.assert_tree(a, ['Basis', 'Same_name', 'b'])
        self.assertEqual(a.data.shape_keys.key_blocks['Same_name'].vertex_group, 'Real vertex group')

    def test_shared_shape_geometry_and_relative_keys_follow_native_join(self):
        a = self.mesh('A', ['Basis', ['Folder', 'shared', 'a_only']])
        b = self.mesh('B', ['Basis', ['Folder', 'shared', 'b_only']])
        a.data.shape_keys.key_blocks['shared'].data[0].co.z = 1
        b.data.shape_keys.key_blocks['shared'].data[0].co.z = 2
        a.data.shape_keys.key_blocks['a_only'].relative_key = a.data.shape_keys.key_blocks['shared']
        self.join(a, b)
        self.assert_tree(a, ['Basis', ['Folder', 'shared', 'a_only', 'b_only']])
        keys = a.data.shape_keys.key_blocks
        self.assertEqual(sum(point.co.z for point in keys['shared'].data), 3)
        self.assertEqual(keys['a_only'].relative_key.name, 'shared')

    def test_active_mesh_without_keys(self):
        a = self.mesh('A')
        b = self.mesh('B', ['Basis', ['Folder', 'b']])
        self.join(a, b)
        self.assert_tree(a, ['Basis', ['Folder', 'b']])

    def test_source_mesh_without_keys(self):
        a = self.mesh('A', ['Basis', ['Folder', 'a']])
        b = self.mesh('B')
        self.join(a, b)
        self.assert_tree(a, ['Basis', ['Folder', 'a']])

    def test_join_without_folders_uses_native_behavior(self):
        a = self.mesh('A', ['Basis', 'a'])
        b = self.mesh('B', ['Basis', 'b'])
        self.join(a, b)
        self.assert_tree(a, ['Basis', 'a', 'b'])

    def test_linked_mesh_data_is_captured_per_object(self):
        a = self.mesh('A', ['Basis', ['Folder', 'a']])
        b = bpy.data.objects.new('B', a.data)
        bpy.context.collection.objects.link(b)
        self.join(a, b)
        self.assert_tree(a, ['Basis', ['Folder', 'a']])
        self.assertEqual(len(a.data.vertices), 6)

    def test_reference_names_remain_at_root(self):
        a = self.mesh('A', ['ActiveBasis', ['Folder', 'a']])
        b = self.mesh('B', ['SourceBasis', ['Folder', 'b']])
        self.join(a, b)
        self.assert_tree(a, ['ActiveBasis', ['Folder', 'a', 'b'], 'SourceBasis'])

    def test_hotkey_and_menu_registration(self):
        keymaps = addon.join_support._keymaps
        self.assertEqual(len(keymaps), 1)
        keymap, item = keymaps[0]
        self.assertEqual(keymap.name, 'Object Mode')
        self.assertEqual((item.idname, item.type, item.value, item.ctrl), ('object.skp_join', 'J', 'PRESS', True))
        bpy.context.window_manager.keyconfigs.update()
        user_map = bpy.context.window_manager.keyconfigs.user.keymaps['Object Mode']
        matches = [item.idname for item in user_map.keymap_items
                   if item.active and item.type == 'J' and item.value == 'PRESS' and item.ctrl
                   and not item.shift and not item.alt and not item.oskey]
        self.assertEqual(matches[0], 'object.skp_join')
        self.assertIn('object.join', matches)
        for menu in (bpy.types.VIEW3D_MT_object, bpy.types.VIEW3D_MT_object_context_menu):
            self.assertIn(addon.join_support.draw_join, menu.draw._draw_funcs)

    def test_non_mesh_join_keeps_native_behavior(self):
        objects = []
        for name in ('CurveA', 'CurveB'):
            curve = bpy.data.curves.new(name, 'CURVE')
            spline = curve.splines.new('POLY')
            spline.points[0].co = (0, 0, 0, 1)
            obj = bpy.data.objects.new(name, curve)
            bpy.context.collection.objects.link(obj)
            objects.append(obj)
        self.join(*objects)
        self.assertEqual(len(objects[0].data.splines), 2)
        self.assertEqual(len(bpy.data.objects), 1)

    def test_undo_redo_restores_objects_and_merged_hierarchy(self):
        a = self.mesh('A', ['Basis', ['Folder', 'a']])
        b = self.mesh('B', ['Basis', ['Folder', 'b']])
        self.select(a, b)
        bpy.ops.ed.undo_push(message='Before folder join')
        self.assertEqual(bpy.ops.object.skp_join('EXEC_DEFAULT', True), {'FINISHED'})
        self.assert_tree(a, ['Basis', ['Folder', 'a', 'b']])

        self.assertEqual(bpy.ops.ed.undo(), {'FINISHED'})
        self.assertEqual(set(bpy.data.objects.keys()), {'A', 'B'})
        self.assert_tree(bpy.data.objects['A'], ['Basis', ['Folder', 'a']])
        self.assert_tree(bpy.data.objects['B'], ['Basis', ['Folder', 'b']])

        self.assertEqual(bpy.ops.ed.redo(), {'FINISHED'})
        self.assertEqual(list(bpy.data.objects.keys()), ['A'])
        self.assert_tree(bpy.data.objects['A'], ['Basis', ['Folder', 'a', 'b']])
        addon.memory.changed()
        self.assertEqual(addon.memory.tree.active.tree, ['Basis', ['Folder', 'a', 'b']])


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(JoinFolderTests))
addon.unregister()
assert not addon.join_support._keymaps
for menu in (bpy.types.VIEW3D_MT_object, bpy.types.VIEW3D_MT_object_context_menu):
    assert addon.join_support.draw_join not in menu.draw._draw_funcs
assert bpy.ops.object.join.get_rna_type().identifier == 'OBJECT_OT_join'
bpy.context.window_manager.keyconfigs.update()
user_map = bpy.context.window_manager.keyconfigs.user.keymaps['Object Mode']
assert not any(item.idname == 'object.skp_join' for item in user_map.keymap_items)
assert any(item.idname == 'object.join' and item.type == 'J' and item.ctrl for item in user_map.keymap_items)
if not result.wasSuccessful():
    sys.exit(1)
