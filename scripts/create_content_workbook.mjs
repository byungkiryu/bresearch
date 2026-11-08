/** One-time authoring utility. Routine updates edit input/content.xlsx directly.
 * Run a copy from a temporary directory whose node_modules symlink points to
 * CODEX_PRIMARY_RUNTIME_NODE_MODULES, using CODEX_PRIMARY_RUNTIME_NODE.
 * Arguments: --project /absolute/bresearch --output /absolute/output-directory
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const arg = (name, fallback) => process.argv.includes(name) ? process.argv[process.argv.indexOf(name) + 1] : fallback;
const project = path.resolve(arg('--project', process.cwd()));
const outputDir = path.resolve(arg('--output', path.join(project, '../outputs/bresearch-input')));
const read = async rel => JSON.parse(await fs.readFile(path.join(project, rel), 'utf8'));
const schema = JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON, ['-c',
  'import json,sys;sys.path.insert(0,sys.argv[1]);import content_schema as s;print(json.dumps({"sheets":s.SHEETS,"help":s.HELP,"home":s.HOME_DEFAULTS,"profileKinds":s.PROFILE_KINDS,"profileScalars":s.PROFILE_SCALARS},ensure_ascii=False))',
  path.join(project, 'scripts')], {encoding:'utf8'}));
const [site, annotations, publications, presentations] = await Promise.all([
  read('content/site.json'), read('content/items.json'), read('data/publications.json'), read('data/presentations.json')]);
const list = (value, separator='\n') => Array.isArray(value) ? value.join(separator) : value ?? '';
const links = value => Array.isArray(value) ? value.map(x => `${x.label || x.title || x.url}|${x.url}`).join('\n') : value ?? '';
const record = (row, index) => ({...row, order:row.order ?? index + 1, public:row.public ?? !row.hidden});
const rows = {};
rows['사람'] = site.people.map(record);
rows['행사'] = (site.events || []).map(record);
const home = {...schema.home, hero_summary:site.research.intro, research_description:site.research.intro, ...site.home};
rows['홈'] = Object.entries(home).map(([key,value]) => ({key, value:Array.isArray(value) ? value.join('; ') : value}));
rows['연구'] = site.research.topics.map((x,i) => record({...x, details:list(x.details), keywords:list(x.keywords,'; '), links:links(x.links)},i));
rows['프로필'] = schema.profileScalars.map((key,i) => record({id:`profile-${key}`,kind:'scalar',key,value:site.profile[key] || ''},i));
for (const [kind,source] of [['education','education'],['career','career'],['award','awards'],['about','about_sections'],['link','links']]) {
  (site.profile[source] || []).forEach((x,i) => rows['프로필'].push(record({
    ...x,id:x.id || `profile-${kind}-${String(i+1).padStart(4,'0')}`,kind,
    title:kind === 'link' ? x.label : x.title, entries:list(x.entries),
  },rows['프로필'].length)));
}
rows['뉴스'] = site.news.map(record);
rows['자료'] = site.links.map(record);
rows['위치'] = Object.entries(site.maps).flatMap(([group,values]) => values.map((x,i) => record({...x,group},i)));
for (const [sheet, data] of [['논문해설',publications],['발표해설',presentations]]) {
  rows[sheet] = data.map((item,i) => {
    const a = annotations.items[item.id] || {};
    return record({...a, id:item.id, title_reference:item.title,
      tags:list(a.tags,'; '), person_ids:list(a.person_ids,'; '), links:links(a.links),
      featured:a.featured ?? false,
    },i);
  });
}

const workbook = Workbook.create();
const palette = {green:'#194A3C',light:'#E8F0EA',blue:'#174EA6',gray:'#68716D',reference:'#F2F4F2',line:'#DDE5DF'};
const widths = {id:200,name:240,category:180,title:360,affiliation:250,period:180,description:520,url:380,image:310,image_alt:310,order:150,public:190,
  start_date:210,end_date:210,place:310,status:210,key:260,value:700,kicker:250,details:650,keywords:300,links:600,kind:300,organization:430,entries:730,
  date:210,body:650,featured:210,group:260,lat:140,lon:140,title_reference:650,summary:520,tags:300,person_ids:340,event_id:310};
const letters = num => { let x=num+1,s=''; while(x){ x--;s=String.fromCharCode(65+x%26)+s;x=Math.floor(x/26);}return s; };
const isReference = key => ['id','key','title_reference'].includes(key);
const dates = new Set(['date','start_date','end_date']);
const typed = (key,value) => dates.has(key) && typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T12:00:00Z`) : value ?? null;
let tableIndex=0;
for (const [name,keys] of Object.entries(schema.sheets)) {
  const sheet=workbook.worksheets.add(name);
  sheet.showGridLines=false;
  sheet.tabColor=palette.green;
  const data=rows[name];
  const last=Math.max(data.length+2,3);
  const end=letters(keys.length-1);
  const help=keys.map(k=>schema.help[k] || k);
  const matrix=[keys,help,...data.map(x=>keys.map(k=>typed(k,x[k])))];
  sheet.getRange(`A1:${end}${matrix.length}`).values=matrix;
  const body=sheet.getRange(`A1:${end}${last}`);
  body.format.font={name:'Arial',size:11,color:palette.blue};
  body.format.wrapText=true;
  body.format.verticalAlignment='center';
  body.format.rowHeightPx=48;
  // The filter header is row 2, so sorting never moves the machine keys or help.
  const table=sheet.tables.add(`A2:${end}${last}`,true,`Content${++tableIndex}`);
  table.style='TableStyleLight1';
  table.showFilterButton=true;
  sheet.getRange(`A1:${end}1`).format={fill:palette.green,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeightPx:30,verticalAlignment:'center'};
  sheet.getRange(`A2:${end}2`).format={fill:palette.light,font:{name:'Arial',size:10,color:'#244F40'},wrapText:true,rowHeightPx:76,verticalAlignment:'center'};
  for (const [i,key] of keys.entries()) {
    const col=letters(i);
    sheet.getRange(`${col}1:${col}${last}`).format.columnWidthPx=widths[key] || 250;
    if(isReference(key)) sheet.getRange(`${col}3:${col}${last}`).format={fill:palette.reference,font:{name:'Arial',size:11,color:palette.gray}};
    if(dates.has(key)) {
      sheet.getRange(`${col}3:${col}${last}`).setNumberFormat('yyyy-mm-dd');
      sheet.getRange(`${col}3:${col}${last}`).format.horizontalAlignment='center';
    }
    if(['order','lat','lon'].includes(key)) {
      sheet.getRange(`${col}3:${col}${last}`).setNumberFormat(key === 'order' ? '0' : '0.0000');
      sheet.getRange(`${col}3:${col}${last}`).format.horizontalAlignment='right';
    }
    let choices=null;
    if(['public','featured'].includes(key)) choices=['TRUE','FALSE'];
    if(name==='사람' && key==='category') choices=['Members','Alumni','Visitors'];
    if(name==='프로필' && key==='kind') choices=schema.profileKinds;
    if(name==='위치' && key==='group') choices=['collaborations','visits'];
    if(name==='행사' && key==='status') choices=['미확인','예정','확정','완료','보류','취소'];
    if(choices) sheet.getRange(`${col}3:${col}1000`).dataValidation={rule:{type:'list',values:choices}};
  }
  // Fit descriptions while keeping each record together, rather than truncating it.
  data.forEach((item,i)=>{
    const lines=keys.reduce((max,key)=>{
      const text=String(item[key] ?? '');
      const capacity=Math.max(12,Math.floor((widths[key] || 250)/7.3));
      const height=text.split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(line.length/capacity)),0);
      return Math.max(max,height);
    },1);
    sheet.getRange(`A${i+3}:${end}${i+3}`).format.rowHeightPx=Math.min(520,Math.max(44,lines*19+12));
  });
  sheet.freezePanes.freezeRows(2);
  sheet.freezePanes.freezeColumns(1);
}

await fs.mkdir(outputDir,{recursive:true});
workbook.recalculate();
const checks=[];
for (const name of Object.keys(schema.sheets)) checks.push(await workbook.inspect({kind:'region',sheetId:name,range:name==='홈'?'A1:B5':'A1:D5',maxChars:1800,tableMaxRows:5,tableMaxCols:4}));
checks.push(await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Final formula error scan'}));
await fs.writeFile(path.join(outputDir,'verification.ndjson'),checks.map(result=>result.ndjson).join('\n')+'\n');
const ranges={'사람':'A1:D8','행사':'A1:D4','홈':'A1:B9','연구':'A1:D6','프로필':'A1:D8','뉴스':'A1:D6','자료':'A1:D6','위치':'A1:D6','논문해설':'A1:C5','발표해설':'A1:C5'};
for(const [name,range] of Object.entries(ranges)){
  const preview=await workbook.render({sheetName:name,range,scale:1,format:'png'});
  await fs.writeFile(path.join(outputDir,`${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir,'content.xlsx'));
await fs.mkdir(path.join(project,'input'),{recursive:true});
await fs.copyFile(path.join(outputDir,'content.xlsx'),path.join(project,'input/content.xlsx'));
console.log(JSON.stringify({output:path.join(outputDir,'content.xlsx'),counts:Object.fromEntries(Object.entries(rows).map(([k,v])=>[k,v.length]))}));
