import fs from 'node:fs/promises';
import path from 'node:path';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
const root = process.cwd();
const skill = '/Users/sf033/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const runtime = '/Users/sf033/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const { finalizePresentation } = await import(skill + '/container_tools/artifact_tool_utils.mjs');
const deck = Presentation.create({slideSize:{width:1280,height:720}});
const s = deck.slides.add();
s.background.fill = '#F4F8FA';
const ink='#122B3B', muted='#436172', teal='#096D68', border='#C9DBE2';
function box(name,x,y,w,h,fill,stroke='none',geometry='rect'){
  return s.shapes.add({name,geometry,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:stroke==='none'?0:1}});
}
function txt(value,x,y,w,h,size,color=ink,bold=false,alignment='left'){
  const el=box(value,x,y,w,h,'none','none','textbox');
  el.text=value;
  el.text.style={typeface:'Arial',fontSize:size,color,bold,alignment,verticalAlignment:'middle',insets:0,wrap:'none'};
}
function card(x,y,w,h,title,lines,header=teal){
  box(title+' frame',x,y,w,h,'#FFFFFF',border);
  box(title+' header',x,y,w,41,header);
  txt(title,x+16,y+5,w-32,31,22,'#FFFFFF',true);
  lines.forEach((line,i)=>txt(line,x+16,y+50+i*27,w-32,25,19));
}
const shots = [
  {x:64, width:542, label:'1. Describe symptoms and answer follow-up questions', stamp:'3.35.07'},
  {x:674, width:530, label:'2. Review possible causes and medicine information', stamp:'3.35.29'},
];
for (const shot of shots) {
  box(shot.label+' header',shot.x,76,shot.width,38,teal);
  txt(shot.label,shot.x+12,79,shot.width-24,31,18,'#FFFFFF',true);
  const filename = '/Users/sf033/Desktop/Screenshot 2026-11-10 at '+shot.stamp+'\u202fPM.png';
  const blob = await fs.readFile(filename);
  s.images.add({blob,contentType:'image/png',alt:shot.label,fit:'contain',position:{left:shot.x,top:114,width:shot.width,height:484}});
}
const png = await deck.export({slide:s,format:'png',scale:2});
await fs.writeFile(path.join(root,'shahan_mrs/docs/deliverables/mrs-ai-interface-no-heading.png'),new Uint8Array(await png.arrayBuffer()));
