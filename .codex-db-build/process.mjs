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
txt('Medicine Recommendation System',64,34,1152,28,20,teal,true);
txt('Iterative Prototyping Model',64,67,1152,57,46,ink,true);
const x1=64,x2=487,x3=910,w=306;
card(x1,173,w,112,'1. Define requirements',['Decide what the system','should do.']);
card(x2,173,w,112,'2. Build the prototype',['Create a trial version of','the system.']);
card(x3,173,w,112,'3. Test the prototype',['Try sample symptom inputs','and check the responses.']);
card(x3,356,w,112,'4. Review the results',['Look at test results','and user feedback.']);
card(x2,356,w,112,'5. Make a decision',['Does the prototype meet','the requirements?'],'#234C65');
card(x1,356,w,112,'Deliver the system',['Prepare the final version','for use.']);
card(x2,522,w,112,'Improve the prototype',['Fix the problems found,','then repeat the tests.'],'#234C65');
function arrow(glyph,x,y,width,height){
  txt(glyph,x,y,width,height,39,teal,true,'center');
}
arrow('→',370,207,117,40);
arrow('→',793,207,117,40);
arrow('↓',1038,296,50,48);
arrow('←',793,389,117,40);
txt('Yes',370,375,117,22,17,muted,true,'center');
arrow('←',370,397,117,40);
arrow('↓',615,470,50,48);
txt('No',656,480,58,23,17,muted,true);
const rule=(name,x,y,w,h)=>box(name,x,y,w,h,teal);
rule('Return from improvements',40,576,447,3);
rule('Return path',40,319,3,260);
rule('Return to build',40,319,600,3);
rule('Return rise',638,299,3,23);
txt('↺',464,327,28,25,22,teal,true);
txt('Repeat the cycle',492,327,177,25,17,muted,true);
arrow('↑',615,276,50,45);
const preview=await deck.export({slide:s,format:'png',scale:2});
await fs.writeFile(path.join(root,'shahan_mrs/docs/deliverables/iterative-prototyping-model.png'),new Uint8Array(await preview.arrayBuffer()));
