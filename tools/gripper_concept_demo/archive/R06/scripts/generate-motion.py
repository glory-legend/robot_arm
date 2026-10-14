"""Offline illustrative FR3 trajectory. Requires numpy/scipy, not ROS.
Joint origins and bounds come from assets prepared from vendored Franka data.
No collision/dynamics claim: this only verifies flange pose and joint bounds.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R
root = Path(__file__).resolve().parents[1]
data = json.loads((root/'src/robot-data.json').read_text())
origins=[]
for j in data:
    m=np.eye(4)
    m[:3,:3]=R.from_euler('xyz',[j['roll'],j['pitch'],j['yaw']]).as_matrix()
    m[:3,3]=[j['x'],j['y'],j['z']]
    origins.append(m)
lo=np.array([j['lower'] for j in data[:7]])+.0001
hi=np.array([j['upper'] for j in data[:7]])-.0001

def fk(q):
    m=np.eye(4)
    for i in range(7):
        rot=np.eye(4);rot[:3,:3]=R.from_euler('z',q[i]).as_matrix()
        m=m@origins[i]@rot
    return m@origins[7]

def ease(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

def target(t,length):
    high=np.array([.48,-.22,.68]);pick=np.array([.48,-.22,.440])
    entry=np.array([.46,.23,.386+length+.026]);above=np.array([.46,.23,.66])
    home=np.array([.40,-.12,.69])
    keys=[(0,home),(3,pick),(5,pick),(8,high),(18,high),(21,above),(23,entry),(61,np.array([.46,.23,.412])),(65,np.array([.46,.23,.412])),(67,above),(70,home)]
    p=keys[-1][1]
    for (a,pa),(b,pb) in zip(keys,keys[1:]):
        if a<=t<=b:p=pa+(pb-pa)*ease((t-a)/(b-a));break
    tilt=0
    return p,R.from_euler('y',np.pi-tilt).as_matrix()

all_paths={}
for name,length in [('m6',.020),('m8',.035),('m10',.050)]:
    q=np.array([0,-.5,0,-2,0,1.5,.785])
    frames=[];max_pos=0;max_rot=0
    for t in np.linspace(0,70,701):
        p,r=target(t,length)
        previous=q.copy()
        def residual(x):
            m=fk(x)
            return np.r_[ (m[:3,3]-p)*5, R.from_matrix(r@m[:3,:3].T).as_rotvec(), (x-previous)*.00005 ]
        sol=least_squares(residual,q,bounds=(lo,hi),xtol=1e-9,ftol=1e-9,gtol=1e-9,max_nfev=100)
        q=sol.x;m=fk(q)
        pe=np.linalg.norm(m[:3,3]-p);re=np.linalg.norm(R.from_matrix(r@m[:3,:3].T).as_rotvec())
        max_pos=max(max_pos,pe);max_rot=max(max_rot,re)
        if pe>.001 or re>.01:raise RuntimeError(f'{name} t={t} IK residual {pe}, {re}')
        frames.append([round(float(t),4),*[round(float(v),9) for v in q]])
    all_paths[name]=frames
    print(f'{name}: {len(frames)} frames, max position residual {max_pos*1000:.4f} mm, angle {max_rot:.6f} rad')
(root/'src/motion-data.json').write_text(json.dumps(all_paths,separators=(',',':'))+'\n')
