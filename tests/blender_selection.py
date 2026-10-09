"""Run with blender --background --factory-startup --python tests/blender_selection.py."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import bpy


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'facial_shapekeys_selection_test'
spec = importlib.util.spec_from_file_location(
    PACKAGE, ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
addon = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE] = addon
spec.loader.exec_module(addon)
bpy.context.preferences.addons.new().module = PACKAGE
addon.register()


class SelectionCall:
    """Supply modifiers to the real invoke method while using Blender's actual mesh data."""
    def __init__(self, index):
        self.mode = 'TOGGLE'
        self.index = index
        self.range_start = -1

    def execute(self, context):
        return addon.operators.ShapeKeySelect.execute(self, context)


class RecordedLayout:
    def __init__(self, records=None, active=True, operator_context='EXEC_DEFAULT'):
        self.records = records if records is not None else []
        self.active = active
        self.operator_context = operator_context

    def row(self, **kwargs):
        return RecordedLayout(self.records, self.active, self.operator_context)

    def separator(self, **kwargs):
        pass

    def prop(self, **kwargs):
        self.records.append(('prop', kwargs['property'], self.active))

    def operator(self, operator, **kwargs):
        button = SimpleNamespace()
        self.records.append(('operator', operator, self.active, self.operator_context, button))
        return button


class SelectionTests(unittest.TestCase):
    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        mesh = bpy.data.meshes.new('SelectionMesh')
        mesh.from_pydata([(0, 0, 0)], [], [])
        self.obj = bpy.data.objects.new('SelectionMesh', mesh)
        bpy.context.collection.objects.link(self.obj)
        for name in ['Basis'] + ['key_' + str(i) for i in range(1, 7)]:
            self.obj.shape_key_add(name=name, from_mix=False)
        bpy.context.view_layer.update()
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        self.keys = self.obj.data.shape_keys.key_blocks
        self.props = self.obj.data.shape_keys.shape_keys_plus
        addon.core.settings = bpy.context.scene.shape_keys_plus
        addon.memory.frame = {}
        addon.memory.changed()

    def click(self, index, shift=False, ctrl=False):
        # Blender's list row can update the active index before the checkbox runs.
        self.obj.active_shape_key_index = index
        call = SelectionCall(index)
        event = SimpleNamespace(shift=shift, ctrl=ctrl)
        result = addon.operators.ShapeKeySelect.invoke(call, bpy.context, event)
        self.assertEqual(result, {'FINISHED'})

    def assert_selected(self, *indices):
        self.assertEqual(addon.core.key.get_selected_indices(), list(indices))
        self.assertEqual(len(self.props.selections), len(indices))
        for index, key in enumerate(self.keys):
            self.assertEqual(addon.core.key.is_selected(key), index in indices)

    def test_shift_click_selects_both_endpoints_and_every_key_between(self):
        self.click(2)
        self.click(5, shift=True)
        self.assert_selected(2, 3, 4, 5)
        self.assertEqual(self.obj.active_shape_key_index, 5)

    def test_shift_click_selects_upward(self):
        self.click(5)
        self.click(2, shift=True)
        self.assert_selected(2, 3, 4, 5)

    def test_range_preserves_unrelated_checked_keys(self):
        self.click(1)
        self.click(5)
        self.click(3, shift=True)
        self.assert_selected(1, 3, 4, 5)

    def test_repeated_shift_click_never_deselects_or_duplicates_keys(self):
        self.click(2)
        self.click(5, shift=True)
        self.click(5, shift=True)
        self.assert_selected(2, 3, 4, 5)
        self.assertEqual(self.props.select_anchor_name, 'key_2')

    def test_shift_click_without_a_starting_checkbox_selects_only_clicked_key(self):
        self.click(4, shift=True)
        self.assert_selected(4)
        self.click(6, shift=True)
        self.assert_selected(4, 5, 6)

    def test_plain_click_starts_a_new_range_and_can_uncheck(self):
        self.click(2)
        self.click(4, shift=True)
        self.click(6)
        self.click(5, shift=True)
        self.assert_selected(2, 3, 4, 5, 6)
        self.assertEqual(self.props.select_anchor_name, 'key_6')
        self.click(3)
        self.assert_selected(2, 4, 5, 6)

    def test_starting_key_is_retained_after_reordering(self):
        self.click(4)
        self.assertEqual(bpy.ops.object.skp_shape_key_move(type='TOP', selected=True), {'FINISHED'})
        self.assertEqual(self.keys.find('key_4'), 1)
        self.click(3, shift=True)
        self.assertEqual([key.name for key in addon.core.key.get_selected()], ['key_4', 'key_1', 'key_2'])
        self.assert_selected(1, 2, 3)

    def test_deselect_all_and_deleted_anchor_do_not_leave_a_stale_range(self):
        self.click(2)
        bpy.ops.object.skp_shape_key_select(mode='NONE')
        self.click(5, shift=True)
        self.assert_selected(5)
        bpy.ops.object.skp_shape_key_remove(type='DEFAULT_SELECTED')
        self.keys = self.obj.data.shape_keys.key_blocks
        self.click(3, shift=True)
        self.assert_selected(3)

    def test_bulk_selection_still_excludes_basis_and_resets_anchor(self):
        bpy.ops.object.skp_shape_key_select(mode='ALL')
        self.assert_selected(1, 2, 3, 4, 5, 6)
        self.click(4, shift=True)
        self.assert_selected(1, 2, 3, 4, 5, 6)
        bpy.ops.object.skp_shape_key_select(mode='INVERSE')
        self.assert_selected()
        self.click(3, shift=True)
        self.assert_selected(3)

    def test_legacy_index_anchor_is_supported_and_invalid_indices_are_rejected(self):
        addon.core.key.select(2, True)
        self.props.select_anchor = 2
        self.click(4, shift=True)
        self.assert_selected(2, 3, 4)
        self.assertEqual(bpy.ops.object.skp_shape_key_select(mode='RANGE', range_start=0, index=5), {'CANCELLED'})
        self.assertEqual(bpy.ops.object.skp_shape_key_select(mode='TOGGLE', index=0), {'CANCELLED'})
        self.assert_selected(2, 3, 4)

    def test_range_can_cross_folder_headers_and_contents(self):
        self.keys[1].vertex_group = addon.core.folder.generate(children=2, expand=0)
        self.keys[5].vertex_group = addon.core.folder.generate(children=1)
        self.click(2)
        self.click(6, shift=True)
        self.assert_selected(2, 3, 4, 5, 6)

    def test_checkbox_is_active_and_invoked_when_editing_controls_are_dimmed(self):
        self.click(1)
        self.keys[3].mute = True
        layout = RecordedLayout()
        addon.MESH_UL_shape_keys_plus.draw_item(
            None, bpy.context, layout, self.obj.data.shape_keys, self.keys[3], 0,
            self.obj, 'active_shape_key_index', index=3)
        checkbox = next(record for record in layout.records
                        if record[:2] == ('operator', 'object.skp_shape_key_select'))
        self.assertTrue(checkbox[2])
        self.assertEqual(checkbox[3], 'INVOKE_DEFAULT')
        self.assertEqual((checkbox[4].mode, checkbox[4].index), ('TOGGLE', 3))
        self.assertIn(('prop', 'mute', False), layout.records)

    def test_ctrl_click_behavior_is_preserved(self):
        self.click(2)
        self.click(5, ctrl=True)
        self.assert_selected(2, 5)
        self.click(5, ctrl=True)
        self.assert_selected(2)

    def test_range_survives_undo_redo(self):
        self.click(2)
        bpy.ops.ed.undo_push(message='Before range selection')
        bpy.ops.object.skp_shape_key_select('EXEC_DEFAULT', True, mode='RANGE', range_start=2, index=5)
        self.assert_selected(2, 3, 4, 5)
        bpy.ops.ed.undo()
        self.obj = bpy.data.objects['SelectionMesh']
        self.keys = self.obj.data.shape_keys.key_blocks
        self.props = self.obj.data.shape_keys.shape_keys_plus
        self.assert_selected(2)
        bpy.ops.ed.redo()
        self.obj = bpy.data.objects['SelectionMesh']
        self.keys = self.obj.data.shape_keys.key_blocks
        self.props = self.obj.data.shape_keys.shape_keys_plus
        self.assert_selected(2, 3, 4, 5)


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SelectionTests))
addon.unregister()
if not result.wasSuccessful():
    sys.exit(1)
