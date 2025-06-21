# Addon info
bl_info = {
    "name": "Auto LOD",
    "author": "Aelstraz",
    "description": "Auto generates LODs for the selected object",
    "blender": (2, 80, 0),
    "category": "Object",
}

import bpy
import math

class OBJECT_OT_GenerateLOD(bpy.types.Operator):
    # Tooltip
    """Auto generates LODs for the current object, and parents the generated LODs into a LOD Group"""
    # ID
    bl_idname = "object.generate_lod"
    # Display name in the interface
    bl_label = "Auto Generate LODs"
    # Register the undo function for the operator
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        # Check if properties are within valid ranges, and if not set them to a valid range
        if self.lodViewer > self.numberOfLODs:
            self.lodViewer = self.numberOfLODs

        if self.endRatio > self.startRatio:
            self.endRatio = self.startRatio - 0.00001

        if self.endIterations < self.startIterations + self.numberOfLODs:
            self.endIterations = self.startIterations + self.numberOfLODs

        if self.endAngleLimit < self.startAngleLimit + self.numberOfLODs:
            self.endAngleLimit = self.startAngleLimit + self.numberOfLODs

        # Check if any object is selected
        if not bpy.context.selected_objects:
            self.report({"WARNING"}, "No object selected")
            return {'CANCELLED'}
        
        # Check if object has a mesh
        if obj.type != 'MESH':
            self.report({"WARNING"}, "Object has no mesh")
            return {'CANCELLED'}
        
        # Check if object has a parent
        if obj.parent:
            self.report({"WARNING"}, "Object already has a parent")
            return {'CANCELLED'}
        
        # Save the objects name as the parent name
        parentName = obj.name
        # Add the suffix '_LOD0' to the current object
        obj.name = obj.name + '_LOD0'
        # Create a new empty object to be the LOD Group parent
        emptyParent = bpy.data.objects.new(parentName, None)
        emptyParent.location = obj.location
        # Parent the current object to the new LOD Group parent
        obj.parent = emptyParent
        # Add the parent to the current collection
        obj.users_collection[0].objects.link(emptyParent)
        # Make sure the current object isn't hidden
        obj.hide_set(False)

        # Hide object if only showing a single lod and it isn't the index of the currently viewed object
        if self.onlyShowSingleLOD and self.lodViewer != 0:
            obj.hide_set(True)

        # Generate LODs
        if self.numberOfLODs == 1:
            self.createLOD(obj, 1, emptyParent, parentName)
        elif self.numberOfLODs == 2:
            self.createLOD(obj, 1, emptyParent, parentName)
            self.createLOD(obj, 2, emptyParent, parentName)
        else:
            self.createLOD(obj, 1, emptyParent, parentName)

            for i in range(self.numberOfLODs - 2):
                self.createLOD(obj, i + 2, emptyParent, parentName)

            self.createLOD(obj, self.numberOfLODs, emptyParent, parentName)

        return {'FINISHED'}
   
    def createLOD(self, obj, id, parent, parentName):
        # Create linked duplicate of original object
        objClone = obj.copy()
        objClone.data = objClone.data
        # Set duplicated object name to its parent name and the '_LOD' suffix
        objClone.name = parentName + '_LOD' + str(id)
        # Set parent for duplicated object and add it to the current collection
        objClone.parent = parent
        obj.users_collection[0].objects.link(objClone)
        # Make sure duplicated object isn't hidden
        objClone.hide_set(False)

        # Hide object if only showing a single lod and it isn't the index of the currently viewed object
        if self.onlyShowSingleLOD and self.lodViewer != id:
            objClone.hide_set(True)

        # Add decimate modifier to duplicated object and set its decimate type
        decimateMod = objClone.modifiers.new(name="Decimate", type="DECIMATE")
        decimateMod.decimate_type = self.decimateType
        numberOfLODs = 1

        # Only subtract one from number of LODs if its greater than one to avoid dividing by zero
        if self.numberOfLODs > 1:
            numberOfLODs = self.numberOfLODs - 1
        
        # Apply decimate options based on the decimate type
        if self.decimateType == "COLLAPSE":           
            # Calculate the ratio per LOD
            ratioPerObj = (self.startRatio - self.endRatio) / numberOfLODs
            ratio = self.startRatio - ratioPerObj * (id - 1)
            # Apply the ratio and Collapse specific settings
            decimateMod.ratio = ratio
            decimateMod.use_symmetry = self.useSymmetry
            decimateMod.symmetry_axis = self.symmetryAxis
            decimateMod.use_collapse_triangulate = self.triangulate
        elif self.decimateType == "UNSUBDIV":
            # Calculate the ratio per LOD
            ratioPerObj = (self.startIterations - self.endIterations) / numberOfLODs
            ratio = self.startIterations - ratioPerObj * (id - 1)
            # Round up to int
            ratio = math.ceil(ratio)
            # Apply the ratio and Unsubdivide specific settings
            decimateMod.iterations = ratio        
        elif self.decimateType == "DISSOLVE":
            # Calculate the ratio per LOD
            ratioPerObj = (self.startAngleLimit - self.endAngleLimit) / numberOfLODs
            ratio = self.startAngleLimit - ratioPerObj * (id - 1)
            # Convert the angle to radians
            ratio = math.radians(ratio)
            # Apply the ratio and Dissolve specific settings
            decimateMod.angle_limit = ratio
            decimateMod.delimit = {self.delimit}
            decimateMod.use_dissolve_boundaries = self.useBoundaries

    def draw(self, context):
        # Draw the options UI
        layout = self.layout
        mainBox = layout.box()
        mainBox.label(text="Main Options")

        mainBox.row().prop(self, 'onlyShowSingleLOD')
        parentObj = bpy.context.selected_objects[0].parent

        if self.onlyShowSingleLOD:
            mainBox.row().prop(self, 'lodViewer')
            faceCount = 0

            if self.lodViewer == 0:
                faceCount = len(parentObj.children[0].data.polygons)
            else:
                decimateModifier = parentObj.children[self.lodViewer].modifiers["Decimate"]
                faceCount = decimateModifier.face_count

            mainBox.row().label(text="Face Count: " + str(faceCount))

        mainBox.row().prop(self, 'numberOfLODs')
        mainBox.row().prop(self, 'decimateType')

        decimateBox = layout.box()
        decimateBox.label(text="Decimate Options")

        if self.decimateType == "COLLAPSE":
            decimateBox.row().prop(self, 'startRatio')
            decimateBox.row().prop(self, 'endRatio')
            decimateBox.row().prop(self, 'useSymmetry')

            if self.useSymmetry:
                 decimateBox.row().prop(self, 'symmetryAxis')
            
            decimateBox.row().prop(self, 'triangulate')
        elif self.decimateType == "UNSUBDIV":
            decimateBox.row().prop(self, 'startIterations')
            decimateBox.row().prop(self, 'endIterations')
        elif self.decimateType == "DISSOLVE":
            decimateBox.row().prop(self, 'startAngleLimit')
            decimateBox.row().prop(self, 'endAngleLimit')
            decimateBox.row().prop(self, 'delimit')
            decimateBox.row().prop(self, 'useBoundaries')

    # General properties
    onlyShowSingleLOD: bpy.props.BoolProperty(name="View Single LOD", default=True)
    lodViewer: bpy.props.IntProperty(name="LOD Viewer", default=0, min=0, soft_max=20, max=20)
    numberOfLODs: bpy.props.IntProperty(name="Number Of LODs", default=3, min=1, max=20)
    decimateType: bpy.props.EnumProperty(name="Decimate Type", items=[('COLLAPSE', "Collapse", "Use edge collapsing."), ('UNSUBDIV', "Unsubdivide", "Use un-subdivide face reduction."), ('DISSOLVE', "Dissolve", "Dissolve geometry to form planar polygons.")], default=0)

    # Collapse properties
    startRatio: bpy.props.FloatProperty(name="Start Ratio", default=0.5, min=0, max=1)
    endRatio: bpy.props.FloatProperty(name="End Ratio", default=0.1, min=0, max=1)
    useSymmetry: bpy.props.BoolProperty(name="Use Symmetry", default=False)
    symmetryAxis: bpy.props.EnumProperty(name="Symmetry Axis", items=[('X', "X", "X Axis"), ('Y', "Y", "Y Axis"), ('Z', "Z", "Z Axis")], default=0)
    triangulate: bpy.props.BoolProperty(name="Triangulate", default=False)

    # Unsubdivide properties
    startIterations: bpy.props.IntProperty(name="Start Iterations", default=1, min=1, max=20)
    endIterations: bpy.props.IntProperty(name="End Iterations", default=2, min=1, max=20)

    # Dissolve properties
    startAngleLimit: bpy.props.FloatProperty(name="Start Angle Limit", default=5, min=1, max=180)
    endAngleLimit: bpy.props.FloatProperty(name="End Angle Limit", default=30, min=1, max=180)
    delimit: bpy.props.EnumProperty(name="Delimit", items=[('NORMAL', "Normal", "Delimit by face directions."), ('MATERIAL', "Material", "Delimit by face material."), ('SEAM', "Seam", "Delimit by edge seams."), ('SHARP', "Sharp", "Delimit by sharp edges."), ('UV', "UV", "Delimit by UV coordinates.")], default=0)
    useBoundaries: bpy.props.BoolProperty(name="Use Boundaries", default=False)

def menu_func(self, context):
    # Display the GenerateLOD operator class as a menu option
    self.layout.operator(OBJECT_OT_GenerateLOD.bl_idname)

def register():
    # Register the GenerateLOD operator class
    bpy.utils.register_class(OBJECT_OT_GenerateLOD)
    # Add the menu_func class which displays a menu option in the object menu
    bpy.types.VIEW3D_MT_object.append(menu_func)  

def unregister():
    # Unregister the GenerateLOD operator class
    bpy.utils.unregister_class(OBJECT_OT_GenerateLOD)
