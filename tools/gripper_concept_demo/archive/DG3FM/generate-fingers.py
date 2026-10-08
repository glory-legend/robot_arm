"""Illustrative DG3FM motion, using upstream URDF frames and limits.
Custom 18 mm narrow bolt tips replace the manufacturer's wide fingertips.
Requires numpy/scipy. Does not solve forces or collisions.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
root=Path(__file__).resolve().parents[1]
urdf=E.parse(root/'public/dg3fm/dg3f_m.urdf').getroot()
def vec(s): return list(map(float,s.split()))
joints=[]
for j in urdf.findall('joint'):
    origin=j.find('origin');axis=j.find('axis');limit=j.find('limit')
    joints.append(dict(name=j.get('name'),parent=j.find('parent').get('link'),child=j.find('child').get('link'),xyz=vec(origin.get('xyz')),rpy=vec(origin.get('rpy')),axis=vec(axis.get('xyz')) if axis is not None else None,lower=float(limit.get('lower')) if limit is not None else None,upper=float(limit.get('upper')) if limit is not None else None))
links={l.get('name'):l.find('visual/geometry/mesh').get('filename').split('/')[-1] for l in urdf.findall('link')}
(root/'src/dg3fm-data.json').write_text(json.dumps(dict(joints=joints,links=links),separators=(',',':'))+'\n')

def fk(q,i):
    m=np.eye(4)
    for j in [joints[0]]+[j for j in joints if j['name'].startswith(f'j_dg_{i+1}_')]:
        tr=np.eye(4);tr[:3,3]=j['xyz'];m=m@tr
        if j['axis']:
            rot=np.eye(4);rot[:3,:3]=R.from_rotvec(np.array(j['axis'])*q[int(j['name'][-1])-1]).as_matrix();m=m@rot
    s=1 if i==0 else -1
    return (m@np.array([s*.018,0,0,1]))[:3],m[:3,:3]@np.array([s,0,0])
def ease(t,a,b):
    v=np.clip((t-a)/(b-a),0,1);return v*v*(3-2*v)
paths={};worst=0
for name,d in [('m6',.006),('m8',.008),('m10',.010)]:
    frames=[];previous=[np.array([a,0,1.5,1]) for a in [0,-np.pi/3,np.pi/3]]
    for t in np.linspace(0,36,361):
        curl=ease(t,10,14);close=ease(t,3,5)*(1-ease(t,16,17));clear=ease(t,17,18)
        rot=R.from_euler('y',.48*(1-curl)).as_matrix();center=np.array([.003*np.sin(np.pi*curl),0,.20-.03*curl])
        qs=[]
        for i,a in enumerate([0,2*np.pi/3,-2*np.pi/3]):
            target=center+rot@np.array([(d/2+.003)*np.cos(a),(d/2+.003)*np.sin(a),.014])
            inward=rot@np.array([-np.cos(a),-np.sin(a),0]);prev=previous[i]
            js=[j for j in joints if j['name'].startswith(f'j_dg_{i+1}_') and j['axis']]
            def residual(q):
                p,n=fk(q,i);return np.r_[(p-target)*100,(n-inward)*.02,(q-prev)*.0001]
            sol=least_squares(residual,prev,bounds=([j['lower']+1e-6 for j in js],[j['upper']-1e-6 for j in js]),max_nfev=100,gtol=1e-9,ftol=1e-9,xtol=1e-9)
            q=sol.x;previous[i]=q
            error=np.linalg.norm(fk(q,i)[0]-target);worst=max(worst,error)
            if error>.0001: raise RuntimeError(f'{name}/{i}/{t}: contact error {error}')
            yaw=[0,-np.pi/3,np.pi/3][i]
            opened=np.array([yaw,0,.9,.5]);stowed=np.array([yaw,0,0,-.5])
            q=(opened+(q-opened)*close)*(1-clear)+stowed*clear
            qs.extend(round(float(v),9) for v in q)
        frames.append(qs)
    paths[name]=frames
(root/'src/finger-motion.json').write_text(json.dumps(paths,separators=(',',':'))+'\n')
print(f'DG3FM: 3 fingers × 4 joints; max fingertip target error {worst*1000:.4f} mm')
