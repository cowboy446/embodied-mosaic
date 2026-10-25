"""Self-contained SVG/HTML inspection of planned and measured navigation."""
import json,math,sys,html
from pathlib import Path
p=Path(sys.argv[1]);grid=json.loads((p/'grid-plan.json').read_text());bounds=json.loads((p/'scene-bounds.json').read_text());report=json.loads((p/'report.json').read_text());audit=json.loads((p/'audit.json').read_text())
r=grid['resolution_m'];ox,oy=grid['origin'];n=grid['size'];xmin,xmax=ox-r/2,ox+(n-.5)*r;ymin,ymax=oy-r/2,oy+(n-.5)*r
W=850;H=850;pad=50;scale=(W-2*pad)/(xmax-xmin)
def xy(x,y):return pad+(x-xmin)*scale,H-pad-(y-ymin)*scale
def rect(x0,y0,x1,y1,attrs):
 x,y=xy(x0,y1);return f'<rect x="{x:.2f}" y="{y:.2f}" width="{(x1-x0)*scale:.2f}" height="{(y1-y0)*scale:.2f}" {attrs}/>'
def linepath(points):return ' '.join(f'{x:.2f},{y:.2f}' for x,y in [xy(*v[:2]) for v in points])
svg=[f'<svg id="map" font-family="Noto Sans CJK SC, sans-serif" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"><defs><clipPath id="clip"><rect x="50" y="50" width="750" height="750"/></clipPath></defs><rect width="850" height="850" fill="#fff"/><g clip-path="url(#clip)">']
svg.append('<g id="occupancy">')
for i,j in grid['occupied']:svg.append(rect(ox+(i-.5)*r,oy+(j-.5)*r,ox+(i+.5)*r,oy+(j+.5)*r,'fill="#f9d8d7"'))
svg.append('</g><g id="boxes">');count=0
for b in bounds['colliders']:
 lo,hi=b['min'],b['max']
 if hi[2]<=.04 or lo[2]>=1.7 or hi[0]<xmin or lo[0]>xmax or hi[1]<ymin or lo[1]>ymax:continue
 # Parent compound colliders contain their child shapes; do not fill their entire bounding span.
 if b['type'] not in ['Mesh','Cube','Cylinder','Capsule','Sphere']:continue
 count+=1;svg.append('<g><title>'+html.escape(b['path'])+f" | Z {lo[2]:.2f}–{hi[2]:.2f}m</title>"+rect(lo[0],lo[1],hi[0],hi[1],('fill="none" stroke="#8056b0" stroke-width="1.5" stroke-dasharray="6 4"' if b['path']=='/World/SceneCollision' else 'fill="#526579" fill-opacity=".12" stroke="#526579" stroke-width="1"'))+'</g>')
svg.append('</g><g id="grid" stroke="#93a3b7" stroke-opacity=".22" stroke-width=".6">')
for i in range(n+1):
 x,_=xy(xmin+i*r,0);_,y=xy(0,ymin+i*r);svg.extend([f'<path d="M{x} 50V800"/>',f'<path d="M50 {y}H800"/>'])
svg.append('</g>');svg.append(f'<polyline points="{linepath(grid["route"])}" fill="none" stroke="#2166d1" stroke-width="4" stroke-dasharray="9 5"/>')
svg.append(f'<polyline id="actual" points="{linepath([s["position"] for s in report["states"]])}" fill="none" stroke="#e58a13" stroke-width="3"/>')
for i,point in enumerate(grid['route']):
 x,y=xy(*point);label='出生点' if i==0 else ('目标' if i==len(grid['route'])-1 else f'路点 {i}')
 svg.append(f'<circle cx="{x}" cy="{y}" r="6" fill="#2166d1"/><text x="{x+10}" y="{y-12}" font-size="16">{label}</text>')
rx,ry=xy(*report['states'][0]['position'][:2]);rh=math.hypot(.55,.55)*scale
svg.append(f'<g id="robot"><rect id="envelope" x="{rx-rh}" y="{ry-rh}" width="{2*rh}" height="{2*rh}" fill="#11a58d" fill-opacity=".12" stroke="#11a58d" stroke-dasharray="4 3"/><circle id="position" cx="{rx}" cy="{ry}" r="6" fill="#11a58d"/></g></g>')
for v in range(math.ceil(xmin),math.floor(xmax)+1):
 x,y=xy(v,ymin);svg.append(f'<text x="{x}" y="825" font-size="13" text-anchor="middle">{v}</text>')
for v in range(math.ceil(ymin),math.floor(ymax)+1):
 x,y=xy(xmin,v);svg.append(f'<text x="40" y="{y+4}" font-size="13" text-anchor="end">{v}</text>')
svg.append('<text x="780" y="845" font-size="14">X / m</text><text x="15" y="25" font-size="14">Y / m ↑</text></svg>');svg=''.join(svg);(p/'grid-topdown.svg').write_text(svg)
data={'states':[{'t':s['time_s'],'p':s['position']} for s in report['states']],'xmin':xmin,'ymin':ymin,'scale':scale}
page='''<!doctype html><html lang="zh"><meta charset="utf-8"><title>Arena G1 · 路径复核</title><style>body{margin:0;background:#f0f3f7;color:#172639;font:16px/1.6 system-ui}main{max-width:1320px;margin:30px auto;padding:0 24px}h1{margin:0}small{color:#62738a}.layout{display:grid;grid-template-columns:minmax(550px,2fr) minmax(280px,1fr);gap:24px;margin-top:24px}.card{background:white;border-radius:14px;padding:20px}svg{width:100%;height:auto}label{display:inline-block;margin-right:14px}input[type=range]{width:100%}li{margin:12px 0}.blue{color:#2166d1}.orange{color:#bf6c08}.red{color:#bd5855}a{color:#2166d1}@media(max-width:850px){.layout{display:block}}</style><main><h1>G1 俯视栅格与行走轨迹</h1><small>Arena · SONIC · 第 14 轮 · 世界坐标，单位米</small><div class="layout"><section class="card">MAP<div><label><input type="checkbox" checked onchange="document.getElementById('boxes').style.display=this.checked?'':'none'">场景碰撞几何 AABB</label><label><input type="checkbox" checked onchange="document.getElementById('occupancy').style.display=this.checked?'':'none'">膨胀禁行区</label><label><input type="checkbox" checked onchange="document.getElementById('actual').style.display=this.checked?'':'none'">实际轨迹</label></div><input id="time" type="range" min="0" step="1"><span id="timeLabel"></span><p><a href="grid-topdown.svg">下载 SVG</a> · <a href="scene-bounds.json">包围盒数据</a> · <a href="grid-plan.json">规划数据</a></p></section><aside class="card"><h2>如何规划</h2><ol><li>出生点周围约 10 × 10 米，41 × 41 个格点，分辨率 0.25 米。</li><li>以机器人半长/半宽 0.45 米，加 0.10 米余量，再取转向包络半宽 √(0.55²+0.55²) ≈ 0.778 米。检测高度 0.04–1.70 米内的碰撞。</li><li>四邻域 BFS 搜索；连接格点的中点也检查。种子 42，从路径长 3–5 米的可达目标中选择一个。</li><li>去掉共线格点、保留拐点。SONIC 生成全身参考动作，50 Hz 控制、300 Hz 物理仿真，使用实际位置切换路点。</li></ol><h2>图例</h2><p class="blue">蓝虚线：规划路径，4.25 米</p><p class="orange">橙实线：逐步记录的实际轨迹</p><p class="red">浅红格：考虑机器人尺寸后的禁行区</p><p>灰框：USD 碰撞几何的世界轴对齐包围盒；悬停查看名称。仅显示与机器人高度范围相交的几何，不画地板和天花板。紫色虚线为合并碰撞网格 SceneCollision 的整体包围盒，内部不一定都是障碍。AABB 是外包框，非物体精确轮廓；规划使用 PhysX 查询，而非灰框。</p><p>绿色方框：当前机器人查询包络。拖动时间轴查看位置。</p><h2>本轮结果</h2><p>约 9.83 秒结束；终点误差 3.47 厘米。独立停稳检查通过，294 帧均未触发黑帧检查。</p><p>394 / 1681 格被占用。完整接触、场景碰撞体覆盖率与地面支撑验收仍待完成。</p></aside></div></main><script>const D=DATA;let slider=document.getElementById('time');slider.max=D.states.length-1;function draw(){let s=D.states[+slider.value],x=50+(s.p[0]-D.xmin)*D.scale,y=800-(s.p[1]-D.ymin)*D.scale,h=Math.hypot(.55,.55)*D.scale;let c=document.getElementById('position');c.setAttribute('cx',x);c.setAttribute('cy',y);let e=document.getElementById('envelope');for(let [k,v] of Object.entries({x:x-h,y:y-h,width:2*h,height:2*h}))e.setAttribute(k,v);document.getElementById('timeLabel').textContent=s.t.toFixed(2)+' s · XY ('+s.p[0].toFixed(2)+', '+s.p[1].toFixed(2)+') m'}slider.oninput=draw;draw();</script></html>'''.replace('MAP',svg).replace('DATA',json.dumps(data));(p/'grid-review.html').write_text(page)
print(p/'grid-review.html',count,'nearby collider bounds')
