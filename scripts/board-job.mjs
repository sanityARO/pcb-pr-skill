// Node 18+, run against the user's local easyeda-api bridge.
import { writeFile } from 'node:fs/promises';
import { createHash, randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';

const [action, project, board, output, resume] = process.argv.slice(2);
const actions = ['snapshot', 'pour-save', 'drc', 'gerber'];
if (!actions.includes(action) || !project || !board || !output) {
  console.error('node board-job.mjs snapshot|pour-save|drc|gerber PROJECT_UUID PCB_UUID NEW_OUTPUT [JOB_UUID]');
  process.exit(2);
}
const port = Number(process.env.EASYEDA_BRIDGE_PORT || 49620);
const base = 'http://127.0.0.1:' + port;
const health = await (await fetch(base + '/health')).json();
if (health.service !== 'easyeda-bridge' || !health.edaConnected) throw Error('Connect the local EasyEDA window first');
const windowId = process.env.EASYEDA_WINDOW_ID || (health.edaWindowCount === 1 && health.activeWindowId);
if (!windowId) throw Error('Choose the window from /eda-windows and set EASYEDA_WINDOW_ID');

async function execute(code) {
  const r = await (await fetch(base + '/execute', {method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({windowId, code}), signal: AbortSignal.timeout(40000)})).json();
  if (!r.success) throw Error(r.error || 'Gateway error');
  return r.result;
}
const guard = 'const check=async()=>{const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();' +
  'if(!d||d.documentType!==3||d.parentProjectUuid!==' + JSON.stringify(project) +
  '||d.uuid!==' + JSON.stringify(board) + ')throw Error("Active PCB changed");};await check();';
const { access } = await import('node:fs/promises');
try { await access(output); throw Error('Use a new output filename'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
if (action === 'snapshot') {
  const source = await execute(guard + 'const s=await eda.sys_FileManager.getDocumentSource();await check();return s;');
  if (typeof source !== 'string' || !source.includes('"COMPONENT"') || !source.split('\n')[0].includes(board))
    throw Error('Incomplete or unsupported board source');
  await writeFile(output, source, {flag:'wx'});
} else {
  const job = resume || randomUUID();
  const key = JSON.stringify(['pcb-pr', project, board, action, job].join(':'));
  console.log('Job', job, 'Window', windowId);
  const bodies = {
    'pour-save': 'const pours=await eda.pcb_PrimitivePour.getAll();if(!pours.length)throw Error("No pour regions");const ids=[];for(const p of pours){await check();if(!await p.rebuildCopperRegion())throw Error("Failed pour "+p.getState_PrimitiveId());ids.push(p.getState_PrimitiveId());}await check();if(!await eda.pcb_Document.save())throw Error("Save failed");return {ids,saved:true};',
    drc: 'const raw=await eda.pcb_Drc.check(true,false,true);if(!Array.isArray(raw))throw Error("Unexpected DRC response");await check();return {raw};',
    gerber: 'const f=await eda.pcb_ManufactureData.getGerberFile("pcb_pr_check");if(!f)throw Error("Empty export");const b=new Uint8Array(await f.arrayBuffer());await check();const chars="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";const parts=[];let s="";for(let i=0;i<b.length;i+=3){const n=(b[i]<<16)|((b[i+1]||0)<<8)|(b[i+2]||0);s+=chars[n>>>18]+chars[(n>>>12)&63]+(i+1<b.length?chars[(n>>>6)&63]:"=")+(i+2<b.length?chars[n&63]:"=");if(s.length>=160000){parts.push(s);s="";}}if(s)parts.push(s);globalThis[k+"_parts"]=parts;return {bytes:b.length,parts:parts.length};'
  };
  const prefix = guard + 'const k=' + key + ';';
  if (!resume) {
    try {
      await execute(prefix + 'if(globalThis[k])throw Error("Job ID in use");globalThis[k]={state:"running"};' +
        'const run=async()=>{' + bodies[action] + '};void run().then(value=>globalThis[k]={state:"done",value},e=>globalThis[k]={state:"failed",error:String(e)});return true;');
    } catch (e) { console.error('Launch reply:', e.message, 'Checking the same job.'); }
  }
  let result;
  for (let i=0; i<36; i++) {
    let state;
    try { state = await execute(prefix + 'return globalThis[k]||null;'); }
    catch (e) { console.error(e.message); await delay(2000); continue; }
    if (!state) throw Error('Job state unavailable. Read back the board before retrying any write.');
    if (state.state === 'failed') throw Error(state.error);
    if (state.state === 'done') { result = state.value; break; }
    await delay(2000);
  }
  if (!result) throw Error('No completion receipt. Poll again with the same job UUID.');
  if (action === 'gerber') {
    const chunks = [];
    for (let i=0; i<result.parts; i++) {
      const part = await execute(prefix + 'return globalThis[k+"_parts"]?.[' + i + ']||null;');
      if (!part) throw Error('Export chunk missing');
      chunks.push(Buffer.from(part,'base64'));
    }
    const bytes = Buffer.concat(chunks);
    if (bytes.length !== result.bytes || bytes.readUInt32LE(0) !== 0x04034b50) throw Error('Incomplete ZIP');
    await writeFile(output,bytes,{flag:'wx'});
    console.log('SHA-256',createHash('sha256').update(bytes).digest('hex'));
    await execute(prefix + 'delete globalThis[k+"_parts"];return true;');
  } else {
    await writeFile(output,JSON.stringify({project,board,action,job,...result},null,2),{flag:'wx'});
  }
}
