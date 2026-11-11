"""Bounded offline SketchUp/Collada import; runtime uses converted RX3 only."""
from pathlib import Path
import math,xml.etree.ElementTree as ET
from functools import lru_cache
import numpy as np


class Collada:
    def __init__(self,path):
        self.path=Path(path);self.root=ET.parse(path).getroot();self.ns={'c':self.root.tag.split('}')[0][1:]}
        self.ids={v.get('id'):v for v in self.root.iter() if v.get('id')}
        self.unit=float(self.root.find('c:asset/c:unit',self.ns).get('meter','1'))*100
        axis=self.root.findtext('c:asset/c:up_axis',default='Y_UP',namespaces=self.ns)
        self.axes=np.array([[1,0,0],[0,0,1],[0,-1,0]],float) if axis=='Z_UP' else np.eye(3)
        if axis not in ('Z_UP','Y_UP') or not 0<self.unit<=1000:raise ValueError('Unsupported source units')
    def find(self,node,path):return node.find(path,self.ns)
    def all(self,node,path):return node.findall(path,self.ns)
    def text(self,node,path,default=''):return node.findtext(path,default=default,namespaces=self.ns)
    def transform(self,node):
        m=np.eye(4)
        for v in node:
            kind=v.tag.split('}')[-1]
            if kind not in ('matrix','translate','rotate','scale'):continue
            a=np.fromstring(v.text or '',sep=' ');x=np.eye(4)
            if kind=='matrix':x=a.reshape(4,4)
            elif kind=='translate':x[:3,3]=a
            elif kind=='scale':x[:3,:3]=np.diag(a)
            else:
                n=a[:3]/np.linalg.norm(a[:3]);angle=math.radians(a[3]);cross=np.array([[0,-n[2],n[1]],[n[2],0,-n[0]],[-n[1],n[0],0]])
                x[:3,:3]=np.eye(3)*math.cos(angle)+(1-math.cos(angle))*np.outer(n,n)+math.sin(angle)*cross
            m=m@x
        if not np.isfinite(m).all():raise ValueError('Non-finite source transform')
        return m
    @lru_cache(maxsize=1500)
    def geometry(self,ident):
        mesh=self.find(self.ids[ident],'c:mesh');arrays={};vertices={}
        for source in self.all(mesh,'c:source'):
            data=np.fromstring(self.text(source,'c:float_array'),sep=' ');access=self.find(source,'c:technique_common/c:accessor');stride=int(access.get('stride','1'));count=int(access.get('count'));offset=int(access.get('offset','0'))
            arrays[source.get('id')]=data[offset:offset+count*stride].reshape(count,stride)
        for v in self.all(mesh,'c:vertices'):
            vertices[v.get('id')]={i.get('semantic'):i.get('source')[1:] for i in self.all(v,'c:input')}
        result=[]
        for triangles in self.all(mesh,'c:triangles'):
            inputs=self.all(triangles,'c:input');stride=1+max(int(i.get('offset')) for i in inputs);raw=np.fromstring(self.text(triangles,'c:p'),sep=' ',dtype=np.int64).reshape(-1,stride)
            if len(raw)!=3*int(triangles.get('count')):raise ValueError('Invalid Collada index list')
            unique,index=np.unique(raw,axis=0,return_inverse=True);values={}
            for i in inputs:
                semantic=i.get('semantic');source=i.get('source')[1:];at=int(i.get('offset'));keys=vertices[source] if semantic=='VERTEX' else {semantic:source}
                for key,value in keys.items():
                    if key=='TEXCOORD' and i.get('set','0')!='0':continue
                    values[key]=arrays[value][unique[:,at]]
            p=values['POSITION'][:,:3];normal=values.get('NORMAL',np.zeros_like(p))[:,:3];uv=values.get('TEXCOORD',np.zeros((len(p),2)))[:,:2]
            result.append(dict(p=p,n=normal,uv=uv,idx=index.astype('<u4'),material=triangles.get('material')))
        return result
    @lru_cache(maxsize=120)
    def material(self,ident):
        mat=self.ids[ident];effect=self.ids[self.find(mat,'c:instance_effect').get('url')[1:]];profile=self.find(effect,'c:profile_COMMON');technique=self.find(profile,'c:technique');shader=next(iter(technique));diffuse=self.find(shader,'c:diffuse')
        color=self.find(diffuse,'c:color');texture=self.find(diffuse,'c:texture');image=None;rgba=[.65,.65,.65,1.]
        if color is not None:rgba=np.fromstring(color.text,sep=' ').tolist()
        if texture is not None:
            params={p.get('sid'):p for p in self.all(profile,'c:newparam')};sampler=params[texture.get('texture')];surface=params[self.text(sampler,'c:sampler2D/c:source')]
            image_id=self.text(surface,'c:surface/c:init_from');relative=self.text(self.ids[image_id],'c:init_from')
            image=(self.path.parent/relative).resolve()
            if not image.is_relative_to(self.path.parent.resolve()) or not image.is_file():raise ValueError('Missing or external Collada texture')
        return dict(id=ident,name=mat.get('name',ident),color=rgba,image=image)
    def extract(self,ident):
        result=[]
        def visit(node,parent,stack):
            name=node.get('id')
            if name and name in stack:raise ValueError('Cyclic Collada instances')
            stack=stack+([name] if name else []);m=parent@self.transform(node)
            for instance in self.all(node,'c:instance_geometry'):
                bindings={v.get('symbol'):v.get('target')[1:] for v in self.all(instance,'c:bind_material/c:technique_common/c:instance_material')}
                for mesh in self.geometry(instance.get('url')[1:]):
                    p=(mesh['p']@m[:3,:3].T+m[:3,3])@self.axes.T*self.unit
                    n=mesh['n']@np.linalg.inv(m[:3,:3])@self.axes.T;n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-10)
                    idx=mesh['idx'].copy().reshape(-1,3)
                    if np.linalg.det(m[:3,:3])<0:idx=idx[:,[0,2,1]]
                    material=self.material(bindings[mesh['material']])
                    result.append(dict(p=p,n=n,uv=mesh['uv'].copy(),idx=idx.reshape(-1),material=material))
            for child in self.all(node,'c:node'):visit(child,m,stack)
            for child in self.all(node,'c:instance_node'):visit(self.ids[child.get('url')[1:]],m,stack)
        visit(self.ids[ident],np.eye(4),[])
        if not result:raise ValueError('Empty equipment component')
        return result
