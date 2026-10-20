"""Stage JSON validation shared with the game workshop; no game data bundled."""
import re
MOTION_MAX_TRAVEL=512
MOTION_MAX_PERIOD=1800
MAX_SAVED_FLAGS=32
GAUNTLET_THEME=11
FOE_KINDS=41
class StageValidationError(ValueError):
    def __init__(self,issues):
        self.issues=issues
        super().__init__(' '.join(issue['message'] for issue in issues))

def trap_issues(stage):
    """Report each bad moving-spike field, retaining editor object identities."""
    if not isinstance(stage,dict) or not isinstance(stage.get('traps',[]),list):return []
    issues=[];width=stage.get('width',8000);height=stage.get('height',160)
    if type(width) is not int or type(height) is not int:return []
    rules=[('x','X position',0,width-1),('y','Y position',25,height-1),('w','Width',8,100),('h','Height',4,height-30),('axis','Travel direction',0,1),('travel','Travel',0,MOTION_MAX_TRAVEL),('period','Cycle',60,MOTION_MAX_PERIOD)]
    for index,p in enumerate(stage.get('traps',[])):
        if not isinstance(p,dict):continue
        for field,label,lo,hi in rules:
            value=p.get(field)
            if type(value) is int and lo<=value<=hi:continue
            if field=='period' and type(value) in (int,float):reason=f'Cycle is {value/60:g} seconds; allowed 1-{MOTION_MAX_PERIOD//60} seconds (60-{MOTION_MAX_PERIOD} whole frames).'
            elif field=='axis':reason=f'Travel direction is {value}; choose Left / right (0) or Up / down (1).'
            elif type(value) is not int:reason=f'{label} must be a whole number; allowed {lo}-{hi}.'
            else:reason=f'{label} is {value} px; allowed {lo}-{hi} px.'
            issues.append({'key':'traps','index':index,'field':field,'message':f'Moving spikes #{index+1} (X {p.get("x")}, Y {p.get("y")}): {reason}'})
    return issues

def validate(stage):
    def require(ok,message):
        if not ok:raise ValueError(message)
    def integer(value):return type(value) is int
    require(isinstance(stage,dict),'Stage must be a JSON object.')
    require(stage.get('format')=='datakin-stage-v1','Unsupported stage format.')
    require(isinstance(stage.get('name'),str) and re.fullmatch(r'[A-Z0-9 ]{1,15}',stage['name']) is not None,'Name must use 1-15 uppercase letters, numbers or spaces.')
    height=stage.get('height',160);require(integer(height) and 160<=height<=2048,'Height must be 160-2048 pixels.')
    width=stage.get('width');require(integer(width) and 240<=width<=8000,'Width must be 240-8000 pixels.')
    require(type(stage.get('theme')) is int and 0<=stage['theme']<=GAUNTLET_THEME,f'Theme must be 0 through {GAUNTLET_THEME}.')
    require(type(stage.get('draft')) is bool,'Draft must be true or false.')
    clean={k:stage[k] for k in ['format','name','width','theme','draft']}
    clean['height']=height
    headroom=stage.get('headroom',0)
    require(integer(headroom) and 0<=headroom<=height-160,'Invalid space above.')
    if headroom:clean['headroom']=headroom
    for name in ['spawn','checkpoint','exit']:
        p=stage.get(name);require(isinstance(p,dict),f'{name} marker is missing.')
        require(all(integer(p.get(k)) for k in ['x','y']),f'{name} coordinates must be integers.')
        require(0<=p['x']<=width-(18 if name=='exit' else 26) and 25<=p['y']<=height-28,f'{name} marker is outside playable bounds.')
        clean[name]={'x':p['x'],'y':p['y']}
    # Planning markers are preserved in JSON; runtime activation comes later.
    for name in ['miniboss_entry','miniboss_exit','road_entry','road_return','flight_start','flight_end','spiral','spiral_exit']:
        if name not in stage or stage[name] is None:continue
        p=stage[name]
        require(isinstance(p,dict) and all(integer(p.get(k)) for k in ['x','y']),f'Invalid {name} marker.')
        require(0<=p['x']<=width-26 and 25<=p['y']<=height-28,f'{name} marker is outside playable bounds.')
        clean[name]={'x':p['x'],'y':p['y']}
    for name in ['platforms','enemies','pickups']:
        items=stage.get(name);require(isinstance(items,list),f'{name} must be a list of objects.')
        clean[name]=[]
        for p in items:
            keys=['x','y','w','h'] if name=='platforms' else ['x','y']
            require(isinstance(p,dict) and all(integer(p.get(k)) for k in keys),f'{name} coordinates and sizes must be integers.')
            require(0<=p['x']<width and 25<=p['y']<height,f'{name} object is outside the stage.')
            if name=='platforms':require(p['w']>=8 and p['h']>=4 and p['x']+p['w']<=width and p['y']+p['h']<=height,'Platform size is invalid or extends outside stage bounds.')
            item={k:p[k] for k in keys}
            if name=='platforms' and 'ice' in p:
                require(integer(p['ice']) and p['ice'] in (0,1),'Slippery must be 0 or 1.')
                item['ice']=p['ice']
            if name=='enemies':
                item['hp']=p.get('hp',2);item['kind']=p.get('kind',0)
                require(integer(item['hp']) and 1<=item['hp']<=10 and integer(item['kind']) and 0<=item['kind']<FOE_KINDS,'Invalid enemy type or health.')
            clean[name].append(item)
    for name,keys in [('movers',['x','y','w','h','axis','travel','period']),('winds',['x','y','w','h','dx','dy']),('spikes',['x','y','w','h'])]:
        items=stage.get(name,[]);require(isinstance(items,list),f'{name} must be a list of objects.')
        clean[name]=[]
        for p in items:
            require(isinstance(p,dict) and all(integer(p.get(k)) for k in keys),f'Invalid {name} fields.')
            require(0<=p['x']<width and 25<=p['y']<height and p['w']>=8 and p['h']>=4 and p['x']+p['w']<=width and p['y']+p['h']<=height,f'Invalid {name} bounds.')
            if name=='movers':
                require(p['axis'] in (0,1) and 0<=p['travel']<=MOTION_MAX_TRAVEL and 60<=p['period']<=MOTION_MAX_PERIOD,f'Moving platforms need travel of 0-{MOTION_MAX_TRAVEL} px and a cycle of 1-{MOTION_MAX_PERIOD//60} seconds; choose horizontal or vertical travel.')
                require((p['x']+p['w']+p['travel']<=width if p['axis']==0 else p['y']+p['h']+p['travel']<=height),'Mover path outside stage.')
            if name=='winds':require(-900<=p['dx']<=900 and -200<=p['dy']<=200,'Invalid wind strength.')
            item={k:p[k] for k in keys}
            if name=='movers' and 'ice' in p:
                require(integer(p['ice']) and p['ice'] in (0,1),'Slippery must be 0 or 1.')
                item['ice']=p['ice']
            if name=='movers':   # v0.60: an optional timing offset, in ticks, so neighbouring lifts need not move as one
                require(integer(p.get('phase',0)) and 0<=p.get('phase',0)<p['period'],'A moving platform\'s timing offset must be from 0 to just under its cycle (in ticks: 60 a second).')
                item['phase']=p.get('phase',0)
            clean[name].append(item)
    clean['byte_id']=stage.get('byte_id',-1 if clean['theme']==GAUNTLET_THEME else None)
    require(integer(clean['byte_id']) and (0<=clean['byte_id']<=10 or (clean['byte_id']==-1 and clean['theme']==GAUNTLET_THEME)),'Each collectible needs a stable byte_id from 0 to 10 (Gauntlet parts use -1).')
    clean['boss']=stage.get('boss',0);require(integer(clean['boss']) and 0<=clean['boss']<=width-180,'Invalid boss position.')
    clean['comate']=stage.get('comate',{'x':0,'y':0})
    require(isinstance(clean['comate'],dict) and all(integer(clean['comate'].get(k)) for k in ['x','y']),'Invalid comate.')
    require(0<=clean['comate']['x']<width and 0<=clean['comate']['y']<height,'Comate outside stage.')
    cps=stage.get('checkpoints',[stage['checkpoint']]);require(isinstance(cps,list) and 1<=len(cps)<=MAX_SAVED_FLAGS,'Use 1–32 checkpoints; checkpoint state uses 32 flags.')
    clean['checkpoints']=[]
    for p in cps:
        require(isinstance(p,dict) and all(integer(p.get(k)) for k in ['x','y']) and 0<=p['x']<=width-26 and 25<=p['y']<=height-28,'Invalid checkpoint.')
        require(clean['theme'] in (10,GAUNTLET_THEME) or not clean['checkpoints'] or p['x']>clean['checkpoints'][-1]['x'],'Checkpoints must be ordered left to right.')
        clean['checkpoints'].append({k:p[k] for k in ['x','y']})
    terrain=stage.get('terrain',[]);require(isinstance(terrain,list),'Terrain must be a list of segments.')
    clean['terrain']=[]
    for t in terrain:
        require(isinstance(t,dict) and all(integer(t.get(k)) for k in ['x','y','w','rise','ice']),'Invalid terrain fields.')
        require(t['x']>=0 and t['w']>=8 and t['x']+t['w']<=width and 55<=t['y']<=height-10 and 55<=t['y']+t['rise']<=height-10 and t['ice'] in (0,1),'Invalid terrain bounds.')
        require(not clean['terrain'] or t['x']>=clean['terrain'][-1]['x']+clean['terrain'][-1]['w'],'Terrain segments must be ordered and nonoverlapping.')
        clean['terrain'].append({k:t[k] for k in ['x','y','w','rise','ice']})
    issues=trap_issues(stage)
    if issues:raise StageValidationError(issues)
    for name,keys in [('traps',['x','y','w','h','axis','travel','period']),('lasers',['x','y','h','dir','phase'])]:
        values=stage.get(name,[]);require(isinstance(values,list),f'{name} must be a list of hazards.')
        clean[name]=[]
        for v in values:
            require(isinstance(v,dict) and all(integer(v.get(k)) for k in keys),'Invalid metal hazard fields.')
            require(0<=v['x']<width and 25<=v['y']<height and 4<=v['h']<=height-30,'Invalid metal hazard bounds.')
            if name=='traps':require(8<=v['w']<=100 and v['axis'] in (0,1) and 0<=v['travel']<=MOTION_MAX_TRAVEL and 60<=v['period']<=MOTION_MAX_PERIOD,'Invalid trap motion.')
            else:require(v['dir'] in (-1,1) and 0<=v['phase']<300,'Invalid laser timing.')
            clean[name].append({k:v[k] for k in keys})
    # v0.51 Gauntlet: solid crushers that slam along one axis, and storm zones
    # where lightning strikes (after a flashing ground warning).
    clean['crushers']=[]
    for i,v in enumerate(stage.get('crushers',[])):
        keys=['x','y','w','h','axis','travel','period','phase']
        require(isinstance(v,dict) and all(integer(v.get(k)) for k in keys),f'Crusher #{i+1} is missing a whole-number setting.')
        require(0<=v['x'] and 25<=v['y'] and 16<=v['w']<=160 and 16<=v['h']<=160 and v['x']+v['w']<=width and v['y']+v['h']<=height,f'Crusher #{i+1} must be 16-160 px on each side and inside the stage.')
        require(v['axis'] in (0,1) and 16<=abs(v['travel'])<=MOTION_MAX_TRAVEL and 90<=v['period']<=MOTION_MAX_PERIOD and 0<=v['phase']<v['period'],f'Crusher #{i+1} needs a travel of 16-{MOTION_MAX_TRAVEL} px (negative slams up/left) and a cycle of 1.5-30 seconds.')
        end=(v['y']+v['h']+v['travel'] if v['axis'] else v['x']+v['w']+v['travel']) if v['travel']>0 else (v['y']+v['travel'] if v['axis'] else v['x']+v['travel'])
        require((0<=end<=width) if not v['axis'] else (25<=end<=height),f'Crusher #{i+1} slams outside the stage.')
        clean['crushers'].append({k:v[k] for k in keys})
    clean['storms']=[]
    for i,v in enumerate(stage.get('storms',[])):
        keys=['x','y','w','h','period']
        require(isinstance(v,dict) and all(integer(v.get(k)) for k in keys),f'Storm zone #{i+1} is missing a whole-number setting.')
        require(0<=v['x'] and 25<=v['y'] and v['w']>=32 and v['h']>=16 and v['x']+v['w']<=width and v['y']+v['h']<=height,f'Storm zone #{i+1} must be inside the stage.')
        require(90<=v['period']<=MOTION_MAX_PERIOD,f'Storm zone #{i+1} strikes every 1.5-30 seconds.')
        clean['storms'].append({k:v[k] for k in keys})
    for a,b in (('flight_start','flight_end'),('spiral','spiral_exit')):
        require((a in clean)==(b in clean),f'Place both {a} and {b} markers.')
        if a in clean:require(clean['theme']==GAUNTLET_THEME,f'{a} markers are for Gauntlet parts.')
    if 'flight_start' in clean:require(clean['flight_end']['x']>clean['flight_start']['x']+240,'The flight lands at least a screen to the right of the Air Pad.')
    clean['vanish']=stage.get('vanish',[])
    for name in ['grass','waters','vines']:
        clean[name]=stage.get(name,[]);require(isinstance(clean[name],list),name+' must be a list.')
        keys=['x','y','length'] if name=='vines' else ['x','y','w','h']
        for p in clean[name]:
            require(isinstance(p,dict) and all(integer(p.get(k)) for k in keys),'Invalid '+name+' fields')
            require(0<=p['x']<width and 25<=p['y']<height,'Invalid '+name+' position')
            if name=='vines':require(24<=p['length']<=85 and p['y']+p['length']<height-30,'Invalid vine length')
            else:require(p['w']>=8 and p['h']>=4 and p['x']+p['w']<=width and p['y']+p['h']<=height,'Invalid '+name+' bounds')
    require(isinstance(clean['vanish'],list),'Disappearing platforms must be a list of platform references.')
    for entry,index in enumerate(clean['vanish']):
        require(integer(index) and 0<=index<len(clean['platforms']),f'Disappearing platform entry #{entry+1} has an invalid platform reference ({index}). Valid indices are 0-{len(clean["platforms"])-1}. This is a platform reference, not its width or height.')
    require(len(set(clean['vanish']))==len(clean['vanish']),'A platform can only appear once in the disappearing-platform list.')
    for name,keys in [('lava',['x','y','w','h']),('jets',['x','y','h','period','phase']),('rails',['platform','left','right'])]:
        values=stage.get(name,[]);require(isinstance(values,list),name+' must be a list.')
        clean[name]=[]
        for order,v in enumerate(values):
            require(isinstance(v,dict) and all(integer(v.get(k)) for k in keys),'Invalid '+name+' fields.')
            if name=='lava':require(0<=v['x']<width and 100<=v['y']<height and v['w']>=8 and v['h']>=4 and v['x']+v['w']<=width and v['y']+v['h']<=height,'Invalid lava pool.')
            elif name=='jets':require(0<=v['x']<width and 25<=v['y']<height and 16<=v['h']<=120 and v['y']+v['h']<=height and 120<=v['period']<=600 and 0<=v['phase']<v['period'],'Invalid magma jet.')
            else:
                # Steering limits are map positions for the raft's left edge, not widths or offsets.
                raft,count=f'Raft #{order+1}',len(clean['platforms'])
                require(0<=v['platform']<count,f'{raft} rides platform {v["platform"]}, but this stage has platforms 0-{count-1}. Attach the raft to a platform that exists.')
                b=clean['platforms'][v['platform']]
                require(v['left']>=0,f'{raft} has a left limit of {v["left"]} px; the leftmost limit is 0.')
                require(v['left']<=v['right'],f'{raft} has its left limit at X {v["left"]} and its right limit at X {v["right"]}; the left limit cannot sit past the right one.')
                require(v['right']+b['w']<=width,f'{raft} steers right to X {v["right"]}, where a {b["w"]} px raft would end at {v["right"]+b["w"]}, past the {width} px map edge. Use a right limit of {width-b["w"]} or less.')
                require(v['left']<=b['x']<=v['right'],f'{raft} rests at X {b["x"]} but steers between X {v["left"]} and X {v["right"]}. These limits are map positions for the left edge of the raft, so keep the left limit at or below {b["x"]} and the right limit at or above {b["x"]}.')
            clean[name].append({k:v[k] for k in keys})
    clean['caches']=stage.get('caches',[])
    require(isinstance(clean['caches'],list) and len(clean['caches'])<=MAX_SAVED_FLAGS,'Use at most 32 bit caches; save files keep 32 collected-cache flags per stage.')
    for v in clean['caches']:
        require(isinstance(v,dict) and all(integer(v.get(k)) for k in ['x','y','bits']) and 0<=v['x']<width and 25<=v['y']<height and 1<=v['bits']<=99,'Invalid bit cache.')
    clean['chemicals']=stage.get('chemicals',[])
    require(isinstance(clean['chemicals'],list),'Chemical pools must be a list.')
    for v in clean['chemicals']:
        require(isinstance(v,dict) and all(integer(v.get(k)) for k in ['x','y','w','h']) and 0<=v['x']<width and 25<=v['y']<height and v['w']>=8 and v['h']>=4 and v['x']+v['w']<=width and v['y']+v['h']<=height,'Invalid chemical pool.')
    clean['switches']=stage.get('switches',[])
    require(isinstance(clean['switches'],list) and len(clean['switches'])<=5,'Use at most five road switches.')
    for v in clean['switches']:
        require(isinstance(v,dict) and all(integer(v.get(k)) for k in ('x','y')) and 0<=v['x']<width and 25<=v['y']<height,'Invalid road switch.')
    if 'road_entry' in clean:
        # v0.39: Frost's Glacier Run gate needs no switches.
        require('road_return' in clean and ((clean['theme']==10 and len(clean['switches'])==5) or clean['theme']==2),'A road gate needs a road return marker (and, in Cosmic, five switches).')
    # Scripted scenery that used to be fixed in the engine: chemical vats, drippers
    # and acid showers, plus electric floor arcs and conveyor belts.
    for name,keys in [('emitters',['x','y','h','kind','period','phase']),('arcs',['x','y','w','h','period','phase']),('belts',['x','y','w','h','dx','period'])]:
        values=stage.get(name,[]);require(isinstance(values,list),name+' must be a list.')
        clean[name]=[]
        for order,v in enumerate(values):
            label={'emitters':'Chemical emitter','arcs':'Electric floor arc','belts':'Conveyor belt'}[name]+f' #{order+1}'
            require(isinstance(v,dict) and all(integer(v.get(k)) for k in keys),f'{label} is missing a whole-number setting.')
            require(0<=v['x']<width and 25<=v['y']<height,f'{label} sits outside the stage.')
            if name=='emitters':
                require(0<=v['kind']<=2,f'{label} type must be Vat (0), Dripper (1) or Acid shower (2).')
                require(8<=v['h'] and v['y']+v['h']<=height,f'{label} needs a pour length of at least 8 px that ends inside the stage.')
                require(120<=v['period']<=600,f'{label} cycle must be 2-10 seconds (120-600 frames).')
            else:
                require(v['w']>=8 and v['h']>=4 and v['x']+v['w']<=width and v['y']+v['h']<=height,f'{label} must be at least 8x4 px and stay inside the stage.')
                if name=='arcs':require(60<=v['period']<=MOTION_MAX_PERIOD,f'{label} cycle must be 1-{MOTION_MAX_PERIOD//60} seconds.')
                else:
                    require(-900<=v['dx']<=900 and v['dx']!=0,f'{label} needs a push between -900 and 900, and not zero.')
                    require(v['period']==0 or 60<=v['period']<=MOTION_MAX_PERIOD,f'{label} reverse cycle must be 0 (never reverses) or 1-{MOTION_MAX_PERIOD//60} seconds.')
            if 'phase' in keys:require(0<=v['phase']<v['period'],f'{label} timing offset must be between 0 and one frame under its cycle.')
            clean[name].append({k:v[k] for k in keys})
    clean['spotlights']=[]
    lights=stage.get('spotlights',[])
    require(isinstance(lights,list),'Spotlights must be a list.')
    for i,p in enumerate(lights):
        label=f'Spotlight #{i+1}'
        p=dict(p) if isinstance(p,dict) else p
        if isinstance(p,dict):
            for key,value in [('dir',1),('on',180),('off',180)]:p.setdefault(key,value)
        keys=['x','y','w','h','travel','period','phase','dir','on','off']
        require(isinstance(p,dict) and all(integer(p.get(k)) for k in keys),label+' is missing a whole-number setting.')
        require(0<=p['x'] and 25<=p['y'] and 16<=p['w'] and 24<=p['h'] and p['x']+p['w']<=width and p['y']+p['h']<=height,label+' needs a cone of at least 16x24 px inside the stage.')
        require(0<=p['travel']<=MOTION_MAX_TRAVEL and 120<=p['period']<=MOTION_MAX_PERIOD,label+' sweep must be 0-512 px, with a cycle of 2-30 seconds.')
        require(0<=p['phase']<p['period'],label+' timing offset must be less than its cycle.')
        require(p['dir'] in (-1,1),label+' direction must be Up or Down.')
        require((p['on']==0 and p['off']==0) or (30<=p['on']<=1800 and 30<=p['off']<=1800),label+' needs both On/Off times (0.5-30 seconds), or both zero for always on.')
        clean['spotlights'].append({k:p[k] for k in keys})
    for key in ('shadow_dusk','shadow_library_entry','shadow_blackout_start','shadow_blackout_end'):
        if stage.get(key) is not None:
            p=stage[key];require(isinstance(p,dict) and integer(p.get('x')) and integer(p.get('y')) and 0<=p['x']<width and 25<=p['y']<height,'Invalid '+key+' marker.')
            clean[key]={'x':p['x'],'y':p['y']}
    if 'shadow_blackout_start' in clean or 'shadow_blackout_end' in clean:
        require('shadow_blackout_start' in clean and 'shadow_blackout_end' in clean,'Place both Blackout starts and Blackout ends markers.')
        require(clean['shadow_blackout_end']['x']>clean['shadow_blackout_start']['x'],'Blackout ends must be to the right of Blackout starts.')
    clean['arena']=stage.get('arena',[])
    require(isinstance(clean['arena'],list) and all(integer(i) and 0<=i<len(clean['platforms']) for i in clean['arena']) and len(set(clean['arena']))==len(clean['arena']),'Invalid arena platform indices.')
    clean['clouds']=stage.get('clouds',[])
    require(isinstance(clean['clouds'],list) and all(integer(i) and 0<=i<len(clean['platforms']) for i in clean['clouds']) and len(set(clean['clouds']))==len(clean['clouds']),'Choose distinct, valid cloud platform references.')
    clean['sections']=stage.get('sections',[])
    require(isinstance(clean['sections'],list),'Inserted sections must be a list.')
    for s in clean['sections']:require(isinstance(s,dict) and integer(s.get('x')) and integer(s.get('w')) and 0<=s['x']<=width and 8<=s['w']<=8000,'Invalid inserted section.')
    require(clean['platforms'],'A stage needs at least one platform.')
    warnings=[]
    if len(clean['enemies'])>64 or len(clean['platforms'])+len(clean['movers'])>256:
        warnings.append('Dense layout: more enemies and platforms add work each frame. Test busy areas on your GBA/Pocket.')
    # Every boss but Gale Hawkman, Blizzard Moose and Rumor Mill stands at a fixed height.
    # (In-game Y = editor Y minus the space added above.) Warn rather than refuse.
    boss_floor={3:140,4:132,5:132,7:132,8:132}.get(clean['theme'])
    if clean['boss'] and boss_floor is not None and clean['exit']['y']+28-headroom!=boss_floor:
        warnings.append(f"This boss stands on a floor at Y {boss_floor+headroom}. The exit marker's feet are at Y {clean['exit']['y']+28}; move the arena floor and exit so they sit at Y {boss_floor+headroom}, or the boss will float or sink.")
    if clean['boss'] and clean['theme']==2:
        under=[t['y']+(clean['boss']+100-t['x'])*t['rise']//t['w'] for t in clean['terrain'] if t['x']<=clean['boss']+100<t['x']+t['w']]
        if under and under[0]!=clean['exit']['y']+28:warnings.append(f"The moose follows the arena floor (Y {under[0]}), but the exit marker's feet are at Y {clean['exit']['y']+28}. Put the exit marker at Y {under[0]-28} so the portal and arena walls meet the floor.")
    for marker in ['spawn','checkpoint']:
        p=clean[marker]
        if not any(b['y']==p['y']+28 and p['x']+24>b['x'] and p['x']+2<b['x']+b['w'] for b in clean['platforms']):warnings.append(f'{marker.title()} is not standing directly on a platform; check the landing position.')
    return clean,warnings
