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
txt('Database and data storage diagram',64,67,1152,57,46,ink,true);
txt('Reference and training data  /  JSON files',64,153,1152,30,24,ink,true);
card(64,195,306,169,'conditions.json',['name','description','medications, diet, precautions','workout, symptoms']);
card(487,195,306,169,'training.json',['id','condition','symptoms  (list of IDs)','source_rows']);
card(910,195,306,169,'symptoms.json',['id','label','aliases','source_severity_weight']);
for (const [x,label,glyph] of [[370,'by name','←'],[793,'by ID','→']]) {
  txt(label,x,242,117,23,17,muted,false,'center');
  txt(glyph,x,265,117,40,39,teal,true,'center');
}
txt('Each training example names one condition and lists the symptom IDs present.',64,374,1152,27,19,muted);
box('divider',64,420,1152,1,border);
txt('Server storage  /  SQLite',64,438,700,30,24,ink,true);
txt('Browser storage  /  localStorage',823,438,393,30,24,ink,true);
card(64,480,722,155,'events',['event_id  (primary key), occurred_at, session_id, conversation_id','condition, symptoms, medicines, intent','urgent, withheld, uncertain'],'#234C65');
card(823,480,393,155,'Conversation history',['Saved conversations and messages'],'#234C65');
txt('One analytics row per completed assistant reply.',64,645,722,27,19,muted);
s.speakerNotes.text='Sources: shahan_mrs/scripts/prepare_json.py (JSON schema and links); shahan_mrs/src/services/analytics.py (SQLite schema); shahan_mrs/docs/implementation.md (browser history and analytics). The arrows indicate lookup fields in JSON. The events table does not declare foreign keys. Other JSON metadata fields and unrelated datasets are omitted for readability.';
const build=path.join(root,'.codex-db-build');
const preview=await deck.export({slide:s,format:'png',scale:1});
await fs.writeFile(path.join(build,'preview.png'),new Uint8Array(await preview.arrayBuffer()));
const candidatePath=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(deck)).save(candidatePath);
await finalizePresentation({
  workspaceDir:root,candidatePath,finalPath:path.join(root,'shahan_mrs/docs/deliverables/database-diagram.pptx'),
  pythonExecutable:runtime+'/python/bin/python3',
  integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
  layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
  fontPolicy:{basis:'design',families:['Arial']},
  explicitTotalSlideCount:1,verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json'),
});
