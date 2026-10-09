# Facial-Shapekeys++

A fork of [ShapeKeys+](https://github.com/MichaelGlenMontague/shape_keys_plus) with a big focus on improving the automatization and workflow on Face Tracking blendshapes (ARKit and UE)

Add-on made for [Blender](https://www.blender.org/) which adds a panel containing extra features for creating, sorting, viewing, and driving shape keys.

Automatically hides the default ***Shape Keys*** panel, which can be enabled again via the add-on's preferences. 

---
# Overview
Facial-Shapekeys++ focuses on automatically adding useful list of blendshapes for VRChat and Vtubing, such as creating the Visemes folder, as well as ARKit, Unified Expressions and Blended shapes for Face Tracking.

And you read that right! it uses the folder system made by ShapeKeys+, allowing you to collapse or expand the list, and keep everything tiny and easy to access or move.

---
# Features
Carried from Shapekeys+ it saves you time by decreasing the number of clicks needed for common operations such as moving or copying shape keys. Some QoL features have been added for Face Tracking.

To access these advanced features, you must Click and hold the **Add**, **Copy** or **Remove** buttons.

<img width="36" height="73" alt="image" src="https://github.com/user-attachments/assets/255f71f9-2312-4402-9226-2e4580ff82df" />

## Add
<img width="256" height="194" alt="image" src="https://github.com/user-attachments/assets/9085cb6f-bb5a-4238-83bf-e3755a444b61" />

### From ShapeKeys+
**New Combined:** Gives you access to the Vanilla feature from Blender to combine the active value of Shapekeys into a new one. Has been renamed from *"New Shape from Mix"* to align with the new name.

**New Folder:** Adds an empty shapekey that is treated as a folder with the addon panel, allowing you to collapse it or move all the shapekeys inside it with ease.

### New
Automatically adds folders and empty shapekeys with the nomenclatures for **ARKit, Unified Expressions, UE Blended Shapes, and Visemes**

<img width="227" height="335" alt="image" src="https://github.com/user-attachments/assets/9cb64686-f230-4a22-a346-aa9eaed36eb4" />

Allows you to translate between ARKit <---> UE nomenclatures by duplicating and parenting the new Blendshapes to their respective folders.

## Copy
**Copy Mirrored** Copies a shapekey on its mirrored vertex.

**Copy Inverted** Copies a shapekey as if its value was -1. but with a normalized value (goes from 0 to 1)

## Remove
Allows you to quickly remove ALL shapekeys

---
# TLDR

# Features from the original ShapeKeys+

- **Folders**
> Manage shape keys with folders.

With the add-on enabled, **Ctrl+J** merges equally named shape key folders when joining meshes,
including nested folders and joins of more than two meshes. You can also use **Join (Keep Shape Key
Folders)** in the Object menu or the right-click context menu. Names must match exactly; `Folder_1`
and `Folder_1.001` remain separate. When the same key or folder has different parents, the active
mesh's hierarchy takes precedence, followed by the other meshes. Its folder icons and open/closed
state are retained. Blender still merges equally named blendshapes into a single shape key.
The original **Join** menu entry and scripts calling `bpy.ops.object.join()` use Blender's native
join; scripts can use `bpy.ops.object.skp_join()` to preserve folders.

- **Shape Key Placement**
> Control where shape keys are automatically placed after specific operations.

- **Copy Shape Key**
> Copy the shape key, its driver, and all or some of its properties. Capable of copying and mirroring at the same time. Mirrored copies automatically detect and rename Left/Right (and similar) naming conventions using Blender's own name-flipping logic.

- **Multi-Selection**
> Perform basic operations on multiple shape keys and folders at once. Compatible with “New Combined” as it creates a new shape out of a mix of the selected shape keys, even if some of them currently have a value of 0. Features compatible with multi-selection become exposed when at least one shape key or folder is selected.

- **Driver Sub-Panel**
> View and edit the driver for a shape key’s value directly within the Facial-Shapekeys++ panel.

- **Manual Translation**
> All UI elements are set up for manual translation, with the two current languages being English and Japanese. The language can be configured at any time simply by changing the language property in the shape_keys_plus/config.ini file and restarting Blender.

# New Features

- **Copy Shape Key, Inverted**
> Copies a shapekey as if its value was -1. but with a normalized value (goes from 0 to 1)

- **ARKit / Unified Expressions / Viseme Automation**
> Automatically generates an empty blendshape list with all ARKit, Unified Expressions, UE Blended shapes or Visemes, each parented into an auto-created "---Face Tracking---" folder (Except for Visemes, that one is by itself).

---
# AI Disclaimer

YES, I know

If you don't like AI, feel free to fork this and redo the code yourself, or try to implement the new features from the original add-on. I'm a designer, not a programmer, even though I helped with simple things such as the Blendshape list for each nomenclature, 95% of the modifications are made by Claude, as I can't find anyone who would do these features quick enough, and the original repo has been archived.

With all of that said, the AI didn't generate much bloat and stuck to making the new features with a couple lines of code. The automations are very fast (basically instant tbh) and at the end of the day, it's intended to make my and other people's workflow faster and easier. AI helped me get this tool out and make my work twice as fast, so I can't be upset by that. But it's something YOU should know for transparency.

Despite the AI, this would not have been possible without the original work from [MichaelGlenMontague](https://github.com/MichaelGlenMontague), credited below. Thank you so much for such an amazing add-on, and I'm happy to have directed this new version for my needs.

---
# Credits
[MichaelGlenMontague](https://github.com/MichaelGlenMontague) - Original work on [Shapekeys+](https://github.com/MichaelGlenMontague/shape_keys_plus) from which this project is based on
