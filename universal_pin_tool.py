import maya.cmds as cmds

class UniversalPinTool(object):
    def __init__(self):
        self.window_name = "UniversalPinToolWindow"
        self.window = None
        self.maintain_offset_cb = None
        self.shape_menu = None
        self.ctrl_size_field = None
        self.color_palette = None
        self.pin_btn = None
        self.unpin_btn = None

    def create_pin_tool_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        
        self.window = cmds.window(self.window_name, title="Universal Pin Tool", widthHeight=(330, 260), sizeable=False)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=("both", 12))
        cmds.separator(height=8, style="none")
        cmds.text(label="Select Vertex -> Geometry to Connect", align="center", font="boldLabelFont")
        cmds.separator(height=10, style="in")
        
        self.maintain_offset_cb = cmds.checkBox(label="Maintain Offset", value=True)
        cmds.separator(height=10, style="in")
        cmds.text(label="Control Settings:", align="left", font="boldLabelFont")
        
        lbl_w, field_w = 60, 240
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[lbl_w, field_w])
        cmds.text(label="Shape:", align="left", width=lbl_w)
        self.shape_menu = cmds.optionMenu(width=field_w)
        for shape in ["Circle", "Square", "Cube", "Locator"]:
            cmds.menuItem(label=shape)
        cmds.setParent("..")
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[lbl_w, field_w])
        cmds.text(label="Size:", align="left", width=lbl_w)
        self.ctrl_size_field = cmds.floatField(value=0.5, minValue=0.01, maxValue=10.0, precision=2, width=field_w)
        cmds.setParent("..")
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[lbl_w, field_w])
        cmds.text(label="Color:", align="left", width=lbl_w)
        self.color_palette = cmds.colorIndexSliderGrp(label="", min=1, max=31, value=18, columnWidth3=[1, 144, 90])
        cmds.setParent("..")
        cmds.separator(height=15, style="in")
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[153, 153], adjustableColumn=True)
        self.pin_btn = cmds.button(label="Pin Object", height=40, width=150, backgroundColor=[0.25, 0.4, 0.5], command=self.execute_pin)
        self.unpin_btn = cmds.button(label="Unpin Object", height=40, width=150, backgroundColor=[0.5, 0.4, 0.6], enable=False, command=self.execute_unpin)
        cmds.setParent("..")
        
        cmds.separator(height=8, style="none")
        cmds.showWindow(self.window)

    def create_shape_curves(self, shape_type, r, name_str):
        if shape_type == "Circle":
            return cmds.circle(nr=(0, 1, 0), r=r, name=name_str, ch=False)
        elif shape_type == "Square":
            d = r
            return cmds.curve(d=1, p=[(-d, 0, -d), (d, 0, -d), (d, 0, d), (-d, 0, d), (-d, 0, -d)], name=name_str, os=True)
        elif shape_type == "Cube":
            d = r
            cube_points = [(-d, d, d), (d, d, d), (d, -d, d), (-d, -d, d), (-d, d, d), (-d, d, -d), (d, d, -d), (d, -d, -d), (-d, -d, -d), (-d, d, -d), (-d, -d, -d), (-d, -d, d), (d, -d, d), (d, -d, -d), (d, d, -d), (d, d, d)]
            return cmds.curve(d=1, p=cube_points, name=name_str, os=True)
        elif shape_type == "Locator":
            loc = cmds.spaceLocator(name=name_str)
            shapes = cmds.listRelatives(loc, shapes=True)
            if shapes:
                for attr in ['localScaleX', 'localScaleY', 'localScaleZ']:
                    cmds.setAttr(f"{shapes[0]}.{attr}", r)
            return loc
        return cmds.circle(nr=(0, 1, 0), r=r, name=name_str, ch=False)

    def check_for_deformers(self, mesh_node):
        history = cmds.listHistory(mesh_node) or []
        deformers = cmds.ls(history, type="geometryFilter")
        skin_clusters = cmds.ls(history, type="skinCluster")
        if skin_clusters: 
            print(f"[Pin Tool Info] Skin Cluster found: {skin_clusters}")
        if deformers:
            non_skin = [d for d in deformers if cmds.nodeType(d) != "skinCluster"]
            if non_skin: 
                print(f"[Pin Tool Info] Other deformers found: {non_skin}")
        return bool(deformers)

    def setup_rig_structure(self):
        main_rig_grp, system_outputs_grp = "Universal_Pin_Rig_GRP", "Pin_Outputs_System_GRP"
        if not cmds.objExists(main_rig_grp): 
            main_rig_grp = cmds.group(empty=True, name=main_rig_grp)
        if not cmds.objExists(system_outputs_grp): 
            system_outputs_grp = cmds.group(empty=True, name=system_outputs_grp)
        cmds.parent(system_outputs_grp, main_rig_grp)
        cmds.setAttr(f"{system_outputs_grp}.visibility", 0)
        return main_rig_grp, system_outputs_grp
        
    def execute_pin(self, *args):
        maintain_offset = cmds.checkBox(self.maintain_offset_cb, query=True, value=True)
        shape_type = cmds.optionMenu(self.shape_menu, query=True, value=True)
        size = cmds.floatField(self.ctrl_size_field, query=True, value=True)
        color_idx = cmds.colorIndexSliderGrp(self.color_palette, query=True, value=True) - 1
        
        selection = cmds.ls(selection=True, flatten=True)
        vtx_selection = [sel for sel in selection if ".vtx[" in sel]
        geo_selection = [sel for sel in selection if cmds.nodeType(sel) == "transform" and cmds.listRelatives(sel, shapes=True, type="mesh")]
        
        if len(vtx_selection) != 1 or len(geo_selection) != 1:
            cmds.warning("Selection error! Select exactly 1 vertex and 1 geometry.")
            return
            
        target_vtx, add_geo = vtx_selection[0], geo_selection[0]
        base_mesh_transform = target_vtx.split(".")[0]
        mesh_shapes = cmds.listRelatives(base_mesh_transform, shapes=True, type="mesh") or []
        
        base_mesh_shape = None
        for shape in mesh_shapes:
            if not cmds.getAttr(f"{shape}.intermediateObject"):
                base_mesh_shape = shape
                break
        if not base_mesh_shape:
            cmds.warning(f"No active mesh shape for {base_mesh_transform}")
            return
            
        self.check_for_deformers(base_mesh_shape)
        cmds.undoInfo(openChunk=True)
        try:
            bbox = cmds.xform(add_geo, query=True, worldSpace=True, boundingBox=True)
            geo_center = [(bbox[0] + bbox[3]) / 2.0, (bbox[1] + bbox[4]) / 2.0, (bbox[2] + bbox[5]) / 2.0]
            
            uvs = cmds.polyListComponentConversion(target_vtx, toUV=True)
            uv_flat = cmds.ls(uvs, flatten=True)
            if not uv_flat:
                vtx_index = target_vtx.split("[")[-1].split("]")[0]
                uvs = cmds.polyListComponentConversion(f"{base_mesh_shape}.vtx[{vtx_index}]", toUV=True)
                uv_flat = cmds.ls(uvs, flatten=True)
            if not uv_flat: 
                raise RuntimeError("No valid UV coordinates found.")
                
            uv_values = cmds.polyEditUV(uv_flat[0], query=True)
            u_coord, v_coord = uv_values[0], uv_values[1]
            
            main_rig_grp, system_outputs_grp = self.setup_rig_structure()
            uv_pin_node = cmds.createNode("uvPin", name=f"{add_geo}_uvPinNode")
            pin_loc = cmds.spaceLocator(name=f"{add_geo}_pinOutput")[0]
            cmds.parent(pin_loc, system_outputs_grp)
            
            cmds.connectAttr(f"{base_mesh_shape}.worldMesh[0]", f"{uv_pin_node}.deformedGeometry")
            cmds.setAttr(f"{uv_pin_node}.coordinate[0].coordinateU", u_coord)
            cmds.setAttr(f"{uv_pin_node}.coordinate[0].coordinateV", v_coord)
            cmds.connectAttr(f"{uv_pin_node}.outputMatrix[0]", f"{pin_loc}.offsetParentMatrix")
            
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']: 
                cmds.setAttr(f"{pin_loc}.{attr}", 0)
                
            connect_grp = cmds.group(empty=True, name=f"{add_geo}_Pin_GRP")
            orient_grp = cmds.group(empty=True, name=f"{add_geo}_Orient_GRP")
            cmds.parent(connect_grp, main_rig_grp)
            
            ctl_name = f"{add_geo}_Pin_CTRL"
            ctl = self.create_shape_curves(shape_type, size, ctl_name)
            if isinstance(ctl, list): 
                ctl = ctl[0]
                
            ctl_shapes = cmds.listRelatives(ctl, shapes=True)
            if ctl_shapes:
                for shape in ctl_shapes:
                    cmds.setAttr(f"{shape}.overrideEnabled", 1)
                    cmds.setAttr(f"{shape}.overrideColor", color_idx)
                    
            cmds.select(clear=True)
            jnt = cmds.joint(name=f"{add_geo}_JNT")
            cmds.setAttr(f"{jnt}.visibility", 0)
            
            cmds.parent(orient_grp, connect_grp)
            cmds.parent(ctl, orient_grp)
            cmds.parent(jnt, ctl)
            
            cmds.xform(connect_grp, worldSpace=True, translation=geo_center)
            cmds.xform(connect_grp, worldSpace=True, pivots=geo_center)
            cmds.xform(orient_grp, worldSpace=True, pivots=geo_center)
            
            cmds.skinCluster(jnt, add_geo, maximumInfluences=1, toSelectedBones=True, removeUnusedInfluence=False)
            
            if maintain_offset:
                cmds.parentConstraint(pin_loc, connect_grp, maintainOffset=True)
                cmds.xform(connect_grp, worldSpace=True, pivots=geo_center)
                cmds.xform(orient_grp, worldSpace=True, pivots=geo_center)
            else:
                cmds.matchTransform(connect_grp, pin_loc, position=True, rotation=True)
                cmds.parentConstraint(pin_loc, connect_grp, maintainOffset=False)
                new_center = cmds.xform(ctl, query=True, worldSpace=True, translation=True)
                cmds.xform(connect_grp, worldSpace=True, pivots=new_center)
                cmds.xform(orient_grp, worldSpace=True, pivots=new_center)
                
            cmds.select(ctl, r=True)
            print(f"Success! Sticky rig setup completed for '{add_geo}'.")
            
            if self.unpin_btn and cmds.button(self.unpin_btn, exists=True):
                cmds.button(self.unpin_btn, edit=True, enable=True)
        except Exception as e:
            cmds.warning(f"Execution failed: {str(e)}")
            raise e
        finally: 
            cmds.undoInfo(closeChunk=True)

    def execute_unpin(self, *args):
        selection = cmds.ls(selection=True)
        add_geo = None
        if selection:
            node = selection[0]
            if node.endswith("_Pin_CTRL") and cmds.objExists(node): 
                add_geo = node.replace("_Pin_CTRL", "")
            elif cmds.nodeType(node) == "transform" and cmds.listRelatives(node, shapes=True, type="mesh"): 
                add_geo = node
                
        if not add_geo or not cmds.objExists(add_geo):
            all_ctrls = cmds.ls("*_Pin_CTRL", type="transform")
            if all_ctrls: 
                add_geo = all_ctrls[0].replace("_Pin_CTRL", "")
            else:
                cmds.warning("Unpin Error: Select pinned geometry or its Pin_CTRL to unpin.")
                return
                
        cmds.undoInfo(openChunk=True)
        try:
            history = cmds.listHistory(add_geo) or []
            skin_clusters = cmds.ls(history, type="skinCluster")
            if skin_clusters: 
                cmds.delete(skin_clusters)
                
            main_rig_grp = "Universal_Pin_Rig_GRP"
            if cmds.objExists(main_rig_grp): 
                cmds.delete(main_rig_grp)
                
            is_referenced = False
            try:
                is_referenced = bool(cmds.referenceQuery(add_geo, isNodeReferenced=True))
            except Exception:
                pass

            if not is_referenced:
                transform_attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
                for attr in transform_attrs:
                    attr_path = f"{add_geo}.{attr}"
                    if cmds.objExists(attr_path):
                        cmds.setAttr(attr_path, lock=False)
                print(f"[Unpin] Unlocked transform channels for '{add_geo}'.")
            else:
                print(f"[Unpin] Object '{add_geo}' is a reference. Skipped attribute unlocking to prevent errors.")
                
            if self.unpin_btn and cmds.button(self.unpin_btn, exists=True): 
                cmds.button(self.unpin_btn, edit=True, enable=False)
                
            cmds.select(add_geo, r=True)
            print(f"Success! Unpin completed for '{add_geo}'. Object returned to original state.")
        except Exception as e:
            cmds.warning(f"Unpin execution failed: {str(e)}")
            raise e
        finally: 
            cmds.undoInfo(closeChunk=True)

def onMayaDroppedPythonFile(*args): 
    UniversalPinTool().create_pin_tool_ui()

if __name__ == "__main__": 
    UniversalPinTool().create_pin_tool_ui()