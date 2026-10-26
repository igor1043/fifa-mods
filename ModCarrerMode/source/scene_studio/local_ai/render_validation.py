"""Offline Blender inspection of the actually inferred/retargeted scene."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Flamengo-onze-editavel.blend'))
data=json.loads((ROOT/'build/tests/ai-world.json').read_text());actors={a['playerId']:a for a in data};C=Matrix.Rotation(math.pi/2,4,'X');Ci=C.inverted()
def matrix(values):
 M=C@Matrix([values[i::4] for i in range(4)])@Ci;M.translation*=.01
 for i in range(3):
  column=M.col[i].to_3d().normalized()
  for j in range(3):M[j][i]=column[j]
 return M
for obj in bpy.data.objects:
 if obj.type!='ARMATURE' or obj.get('player_id') not in actors:continue
 actor=actors[obj['player_id']];obj.animation_data_clear();p=actor['position'];obj.location=(p[0],-p[2],p[1]);world=[matrix(v) for v in actor['poseWorld']]
 for i,pb in enumerate(obj.pose.bones):
  bone=obj.data.bones[i];kwargs={} if bone.parent is None else dict(parent_matrix=world[list(obj.data.bones).index(bone.parent)],parent_matrix_local=bone.parent.matrix_local)
  pb.matrix_basis=bone.convert_local_to_pose(world[i],bone.matrix_local,invert=True,**kwargs)
scene=bpy.context.scene;scene.camera.location=(0,-8,2.5);scene.camera.rotation_euler=(Vector((0,0,.9))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=5.7;scene.cycles.samples=8;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1300;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.filepath=str(ROOT/'build/tests/ai-retarget-preview.png');bpy.ops.render.render(write_still=True)
print('AI_RETARGET_RENDER_COMPLETE',flush=True)
