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
  {x:61,y:28,label:'1. Symptom chat',stamp:'3.35.07'},
  {x:460,y:28,label:'2. Possible causes',stamp:'3.35.29'},
  {x:859,y:28,label:'3. Health context',stamp:'3.37.30'},
  {x:61,y:371,label:'4. Conversation history',stamp:'3.37.47',crop:{left:0.445,top:0.045,right:0.008,bottom:0.325}},
  {x:460,y:371,label:'5. Conversation analytics',stamp:'3.38.07',crop:{left:0.502,top:0,right:0.08,bottom:0.4}},
  {x:859,y:371,label:'6. About & sources',stamp:'3.38.14',crop:{left:0.496,top:0.09,right:0.09,bottom:0.48}},
];
for (const {x,y,label,stamp,crop} of shots) {
  box(label+' header',x,y,360,32,teal);
  txt(label,x+12,y+2,336,28,18,'#FFFFFF',true);
  const blob=await fs.readFile('/Users/sf033/Desktop/Screenshot 2026-11-10 at '+stamp+'\u202fPM.png');
  box(label+' background',x,y+32,360,288,'#101217');
  s.images.add({blob,contentType:'image/png',alt:label,fit:'contain',crop,position:{left:x,top:y+32,width:360,height:288}});
}
const png=await deck.export({slide:s,format:'png',scale:2});
await fs.writeFile(path.join(root,'shahan_mrs/docs/deliverables/mrs-ai-six-interfaces.png'),new Uint8Array(await png.arrayBuffer()));
