"""Run with blender --background --factory-startup --python tests/blender_sorting.py."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import bpy


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'facial_shapekeys_sorting_test'
spec = importlib.util.spec_from_file_location(
    PACKAGE, ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
addon = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE] = addon
spec.loader.exec_module(addon)
bpy.context.preferences.addons.new().module = PACKAGE
addon.register()


class RecordedLayout:
    def __init__(self, records=None):
        self.records = records if records is not None else []

    def row(self, **kwargs):
        return RecordedLayout(self.records)

    def menu(self, **kwargs):
        pass

    def separator(self):
        pass

    def operator(self, operator, **kwargs):
        button = SimpleNamespace()
        self.records.append((operator, kwargs, button))
        return button


class SortingTests(unittest.TestCase):
    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        mesh = bpy.data.meshes.new('SortingMesh')
        mesh.from_pydata([(0, 0, 0), (1, 0, 0)], [], [])
        self.obj = bpy.data.objects.new('SortingMesh', mesh)
        bpy.context.collection.objects.link(self.obj)
        bpy.context.view_layer.update()
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        addon.memory.frame = {}
        addon.memory.tree.active = None
        addon.core.settings = bpy.context.scene.shape_keys_plus

    def make_tree(self, branch):
        for item in branch:
            folder = isinstance(item, list)
            name = item[0] if folder else item
            key = self.obj.shape_key_add(name=name, from_mix=False)
            if folder:
                key.vertex_group = addon.core.folder.generate(children=len(item) - 1)
                self.make_tree(item[1:])

    @property
    def keys(self):
        return self.obj.data.shape_keys.key_blocks

    @property
    def props(self):
        return self.obj.data.shape_keys.shape_keys_plus

    def check(self, *names):
        for name in names:
            result = bpy.ops.object.skp_shape_key_select(mode='TOGGLE', index=self.keys.find(name))
            self.assertEqual(result, {'FINISHED'})

    def sort(self, order='ASCENDING'):
        self.assertEqual(bpy.ops.object.skp_shape_key_sort(order=order), {'FINISHED'})

    def assert_tree(self, expected):
        self.assertEqual(addon.memory.tree().tree, expected)
        self.assertEqual(list(self.keys.keys()), addon.core.utils.flatten(expected))

    def assert_selected(self, *names):
        self.assertEqual(set(key.name for key in addon.core.key.get_selected()), set(names))
        self.assertEqual(len(self.props.selections), len(names))

    def test_scattered_selection_ascending_leaves_unchecked_rows_in_place(self):
        self.make_tree(['Basis', 'Zeta', 'fixed', 'Alpha', 'middle', 'beta'])
        self.check('Zeta', 'Alpha', 'beta')
        self.sort()
        self.assert_tree(['Basis', 'Alpha', 'fixed', 'beta', 'middle', 'Zeta'])
        self.assert_selected('Zeta', 'Alpha', 'beta')

    def test_scattered_selection_descending(self):
        self.make_tree(['Basis', 'Zeta', 'fixed', 'Alpha', 'middle', 'beta'])
        self.check('Zeta', 'Alpha', 'beta')
        self.sort('DESCENDING')
        self.assert_tree(['Basis', 'Zeta', 'fixed', 'beta', 'middle', 'Alpha'])

    def test_no_selection_or_one_selection_disables_sorting(self):
        self.assertFalse(bpy.ops.object.skp_shape_key_sort.poll())
        self.make_tree(['Basis', 'Zeta', 'Alpha'])
        self.assertFalse(bpy.ops.object.skp_shape_key_sort.poll())
        self.check('Zeta')
        self.assertFalse(bpy.ops.object.skp_shape_key_sort.poll())
        self.assert_tree(['Basis', 'Zeta', 'Alpha'])

    def test_edit_mode_disables_sorting(self):
        self.make_tree(['Basis', 'Zeta', 'Alpha'])
        self.check('Zeta', 'Alpha')
        self.assertTrue(bpy.ops.object.skp_shape_key_sort.poll())
        bpy.ops.object.mode_set(mode='EDIT')
        try:
            self.assertFalse(bpy.ops.object.skp_shape_key_sort.poll())
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')

    def test_basis_cannot_be_sorted_even_with_a_stale_checkbox_entry(self):
        self.make_tree(['ZZZ Reference', 'Zeta', 'Alpha'])
        self.props.selections.add().name = '0'
        self.check('Zeta', 'Alpha')
        self.sort('DESCENDING')
        self.assert_tree(['ZZZ Reference', 'Zeta', 'Alpha'])
        self.sort()
        self.assert_tree(['ZZZ Reference', 'Alpha', 'Zeta'])
        self.assert_selected('Zeta', 'Alpha')

    def test_root_and_each_folder_are_sorted_independently(self):
        self.make_tree(['Basis', ['F1', 'Zulu', 'unchanged', 'Alpha'], 'LooseZ',
                        ['F2', 'Delta', 'keep', 'Charlie'], 'LooseA'])
        self.check('Zulu', 'Alpha', 'Delta', 'Charlie', 'LooseZ', 'LooseA')
        self.sort()
        self.assert_tree(['Basis', ['F1', 'Alpha', 'unchanged', 'Zulu'], 'LooseA',
                          ['F2', 'Charlie', 'keep', 'Delta'], 'LooseZ'])
        self.assert_selected('Zulu', 'Alpha', 'Delta', 'Charlie', 'LooseZ', 'LooseA')

    def test_one_selected_key_per_folder_keeps_membership_and_order(self):
        expected = ['Basis', ['F1', 'Zulu'], ['F2', 'Alpha']]
        self.make_tree(expected)
        self.check('Zulu', 'Alpha')
        self.sort()
        self.assert_tree(expected)
        self.assert_selected('Zulu', 'Alpha')

    def test_selected_folders_move_as_blocks_with_nested_contents(self):
        self.make_tree(['Basis', ['ZuluFolder', 'zchild', 'achild'], 'stay',
                        ['AlphaFolder', ['Nested', 'nchild'], 'inside'], ['MiddleFixed', 'foo']])
        self.keys['ZuluFolder'].vertex_group = addon.core.folder.generate(children=2, expand=0, icons=-8)
        settings = {key.name: key.vertex_group for key in self.keys if addon.core.key.is_folder(key)}
        self.check('ZuluFolder', 'AlphaFolder')
        self.sort()
        self.assert_tree(['Basis', ['AlphaFolder', ['Nested', 'nchild'], 'inside'], 'stay',
                          ['ZuluFolder', 'zchild', 'achild'], ['MiddleFixed', 'foo']])
        self.assertEqual({name: self.keys[name].vertex_group for name in settings}, settings)
        self.assert_selected('ZuluFolder', 'AlphaFolder')

    def test_selected_descendants_sort_without_implicitly_sorting_other_children(self):
        self.make_tree(['Basis', ['Zulu', 'z', 'fixed', 'a'], ['Alpha', 'd', 'c']])
        self.check('Zulu', 'Alpha', 'z', 'a')
        self.sort()
        self.assert_tree(['Basis', ['Alpha', 'd', 'c'], ['Zulu', 'a', 'fixed', 'z']])
        self.assert_selected('Zulu', 'Alpha', 'z', 'a')

    def test_alphabetical_order_ignores_case_and_is_stable_for_equal_names(self):
        self.make_tree(['Basis', 'zeta', 'ALPHA', 'alpha', 'Beta'])
        self.check('zeta', 'ALPHA', 'alpha', 'Beta')
        self.sort()
        self.assert_tree(['Basis', 'ALPHA', 'alpha', 'Beta', 'zeta'])
        self.sort('DESCENDING')
        self.assert_tree(['Basis', 'zeta', 'Beta', 'ALPHA', 'alpha'])

    def test_active_key_selection_anchor_and_following_shift_click_are_preserved(self):
        self.make_tree(['Basis', 'Zulu', 'fixed', 'Alpha', 'middle', 'Beta'])
        self.check('Beta', 'Alpha', 'Zulu')
        self.obj.active_shape_key_index = self.keys.find('middle')
        self.sort()
        self.assertEqual(self.obj.active_shape_key.name, 'middle')
        self.assertEqual(self.props.select_anchor_name, 'Zulu')
        self.assertEqual(self.props.select_anchor, self.keys.find('Zulu'))
        self.assert_selected('Beta', 'Alpha', 'Zulu')

        class SelectionCall:
            mode = 'TOGGLE'
            index = 4
            range_start = -1

            def execute(call, context):
                return addon.operators.ShapeKeySelect.execute(call, context)

        result = addon.operators.ShapeKeySelect.invoke(
            SelectionCall(), bpy.context, SimpleNamespace(shift=True, ctrl=False))
        self.assertEqual(result, {'FINISHED'})
        self.assert_selected('Alpha', 'Beta', 'middle', 'Zulu')

    def test_legacy_anchor_is_preserved_by_identity(self):
        self.make_tree(['Basis', 'Zulu', 'Alpha'])
        self.check('Zulu', 'Alpha')
        self.props.select_anchor_name = ''
        self.props.select_anchor = 1
        self.sort()
        self.assertEqual(self.props.select_anchor_name, 'Zulu')
        self.assertEqual(self.props.select_anchor, 2)

    def test_geometry_relative_keys_drivers_and_animation_stay_with_keys(self):
        self.make_tree(['Basis', 'Zulu', 'Alpha'])
        self.keys['Zulu'].data[0].co.z = 3
        self.keys['Alpha'].data[1].co.z = 5
        self.keys['Alpha'].relative_key = self.keys['Zulu']
        self.keys['Zulu'].slider_min = -0.5
        self.keys['Zulu'].slider_max = 2
        self.keys['Zulu'].value = 0.7
        self.keys['Zulu'].vertex_group = 'mask'
        self.keys['Zulu'].mute = True
        driver = self.keys['Alpha'].driver_add('value')
        driver.driver.expression = '0.2'
        self.keys['Zulu'].keyframe_insert('value', frame=1)
        animation = self.obj.data.shape_keys.animation_data
        action = animation.action
        paths = [curve.data_path for curve in animation.drivers]
        self.check('Zulu', 'Alpha')
        self.sort()
        self.assert_tree(['Basis', 'Alpha', 'Zulu'])
        self.assertEqual(self.keys['Zulu'].data[0].co.z, 3)
        self.assertEqual(self.keys['Alpha'].data[1].co.z, 5)
        self.assertEqual(self.keys['Alpha'].relative_key.name, 'Zulu')
        self.assertEqual(self.keys['Zulu'].slider_min, -0.5)
        self.assertEqual(self.keys['Zulu'].slider_max, 2)
        self.assertAlmostEqual(self.keys['Zulu'].value, 0.7)
        self.assertEqual(self.keys['Zulu'].vertex_group, 'mask')
        self.assertTrue(self.keys['Zulu'].mute)
        self.assertEqual(animation.action, action)
        self.assertEqual([curve.data_path for curve in animation.drivers], paths)
        self.assertEqual(animation.drivers[0].driver.expression, '0.2')

    def test_repeated_sort_does_not_duplicate_selections_and_restores_visibility(self):
        self.make_tree(['Basis', 'Zulu', 'Alpha'])
        self.check('Zulu', 'Alpha')
        self.sort()
        self.assertFalse(self.obj.hide_viewport)
        self.assertTrue(self.obj.select_get())
        self.sort()
        self.obj.hide_viewport = True
        was_selected = self.obj.select_get()
        self.sort('DESCENDING')
        self.assertTrue(self.obj.hide_viewport)
        self.assertEqual(self.obj.select_get(), was_selected)
        self.assert_selected('Zulu', 'Alpha')
        self.assert_tree(['Basis', 'Zulu', 'Alpha'])

    def test_dropdown_exposes_both_directions_even_without_selection(self):
        self.make_tree(['Basis', 'Zulu', 'Alpha'])
        for selected in (False, True):
            if selected:
                self.check('Zulu', 'Alpha')
            layout = RecordedLayout()
            addon.menus.ShapeKeyOtherContextMenu.draw(SimpleNamespace(layout=layout), bpy.context)
            buttons = [record for record in layout.records if record[0] == 'object.skp_shape_key_sort']
            self.assertEqual([record[2].order for record in buttons], ['ASCENDING', 'DESCENDING'])
            self.assertEqual([record[1]['text'] for record in buttons],
                             ['Sort Selected A to Z', 'Sort Selected Z to A'])
            self.assertEqual(bpy.ops.object.skp_shape_key_sort.poll(), selected)

    def test_sort_survives_undo_redo_with_selection_and_active_key(self):
        self.make_tree(['Basis', 'Zulu', 'Alpha'])
        self.check('Zulu', 'Alpha')
        self.obj.active_shape_key_index = 1
        bpy.ops.ed.undo_push(message='Before sorting')
        bpy.ops.object.skp_shape_key_sort('EXEC_DEFAULT', True, order='ASCENDING')
        self.assert_tree(['Basis', 'Alpha', 'Zulu'])
        self.assertEqual(self.obj.active_shape_key.name, 'Zulu')
        bpy.ops.ed.undo()
        self.obj = bpy.data.objects['SortingMesh']
        self.assert_tree(['Basis', 'Zulu', 'Alpha'])
        self.assert_selected('Zulu', 'Alpha')
        self.assertEqual(self.obj.active_shape_key.name, 'Zulu')
        bpy.ops.ed.redo()
        self.obj = bpy.data.objects['SortingMesh']
        self.assert_tree(['Basis', 'Alpha', 'Zulu'])
        self.assert_selected('Zulu', 'Alpha')
        self.assertEqual(self.obj.active_shape_key.name, 'Zulu')


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SortingTests))
addon.unregister()
if not result.wasSuccessful():
    sys.exit(1)
