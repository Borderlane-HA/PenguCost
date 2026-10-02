import {useRef,useState} from 'react';
import {FileSpreadsheet,LoaderCircle} from 'lucide-react';
import {api,type Account} from '../lib/api';
import {useI18n} from '../i18n';

type Preview={columns:string[];mapping:Record<string,number|null>;delimiter:string;encoding:string;header_row:number;row_count:number;sample:{line:number;cells:string[]}[]};
const labels={
 de:{title:'CSV ohne KI importieren',help:'Bankexport auswählen, Spalten prüfen und Buchungen einlesen. Es werden noch keine Einträge angelegt. Maximal 20 MB und 2.000 Buchungen.',file:'CSV-Datei',delimiter:'Trennzeichen',encoding:'Zeichenkodierung',header:'Kopfzeile (0 = automatisch)',auto:'Automatisch',preview:'Vorschau laden',unused:'Nicht zugeordnet',date:'Buchungsdatum',merchant:'Empfänger / Auftraggeber',amount:'Betrag mit Vorzeichen',currency:'Währung (sonst EUR)',entry_type:'Buchungsrichtung',reference:'Stabile Vertragsnummer (optional)',debit:'Soll / Belastung',credit:'Haben / Gutschrift',dateFormat:'Datumsformat',direction:'Richtung ohne zugeordnete Richtungsspalte',signed:'Minus = Ausgabe, Plus = Einnahme',expense:'Alle als Ausgaben',income:'Alle als Einnahmen',account:'Konto für neue Einträge',later:'Später zuordnen',import:'Buchungen einlesen',rows:'Buchungen',columnsHelp:'Datum und Empfänger sowie Betrag oder beide Spalten Soll/Haben zuordnen. Ohne Währungsspalte wird EUR verwendet. Bei Beträgen ohne Vorzeichen die Richtung ausdrücklich wählen.',line:'Zeile',dmy:'Tag.Monat.Jahr / Tag/Monat/Jahr',mdy:'Monat/Tag/Jahr',iso:'Jahr-Monat-Tag',confirm:'Spalten, Datumsformat, Währung und Buchungsrichtung anhand der Vorschau geprüft.',tab:'Tabulator'},
 en:{title:'Import CSV without AI',help:'Select a bank export, check the columns and read bookings. Entries are created only after review. Up to 20 MB and 2,000 bookings.',file:'CSV file',delimiter:'Delimiter',encoding:'Encoding',header:'Header row (0 = automatic)',auto:'Automatic',preview:'Load preview',unused:'Not mapped',date:'Booking date',merchant:'Payee / payer',amount:'Signed amount',currency:'Currency (otherwise EUR)',entry_type:'Booking direction',reference:'Stable contract reference (optional)',debit:'Debit',credit:'Credit',dateFormat:'Date format',direction:'Direction when no direction column is mapped',signed:'Negative = expense, positive = income',expense:'All as expenses',income:'All as income',account:'Account for new entries',later:'Assign later',import:'Read bookings',rows:'bookings',columnsHelp:'Map date, counterparty and amount, or both debit/credit columns. Currency defaults to EUR. Explicitly choose the direction for unsigned amounts.',line:'Row',dmy:'Day.Month.Year / Day/Month/Year',mdy:'Month/Day/Year',iso:'Year-Month-Day',confirm:'I checked columns, date format, currency and direction against the preview.',tab:'Tab'}
};

export default function StatementCsvImport({accounts,onCreated}:{accounts:Account[];onCreated:(job:any)=>Promise<void>}){
 const {language}=useI18n();const w=labels[language];const input=useRef<HTMLInputElement>(null);
 const [file,setFile]=useState<File|null>(null);const [preview,setPreview]=useState<Preview|null>(null);
 const [delimiter,setDelimiter]=useState('');const [encoding,setEncoding]=useState('auto');const [header,setHeader]=useState(0);
 const [mapping,setMapping]=useState<Record<string,number|null>>({});const [direction,setDirection]=useState('signed');const [format,setFormat]=useState('auto');const [account,setAccount]=useState('');
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [confirmed,setConfirmed]=useState(false);
 const invalidate=()=>{setPreview(null);setConfirmed(false);setError('')};
 const form=()=>{const data=new FormData();if(file)data.append('file',file);data.append('delimiter',delimiter);data.append('encoding',encoding);data.append('header_row',String(header));return data};
 const load=async()=>{if(!file)return;setBusy(true);setError('');setPreview(null);setConfirmed(false);try{const p=await api<Preview>('/api/ai/statements/csv/preview',{method:'POST',body:form()});setPreview(p);setMapping(p.mapping);setDelimiter(p.delimiter);setEncoding(p.encoding);setHeader(p.header_row)}catch(e:any){setError(e.message)}finally{setBusy(false)}};
 const start=async()=>{if(!preview||!confirmed)return;setBusy(true);setError('');try{const data=form();data.append('mapping',JSON.stringify(mapping));data.append('direction',direction);data.append('date_format',format);if(account)data.append('account_id',account);const job=await api('/api/ai/statements/csv/import',{method:'POST',body:data});await onCreated(job);setFile(null);setPreview(null);setConfirmed(false);if(input.current)input.current.value=''}catch(e:any){setError(e.message)}finally{setBusy(false)}};
 const valid=!!preview&&mapping.date!=null&&mapping.merchant!=null&&(mapping.amount!=null||(mapping.debit!=null&&mapping.credit!=null));
 return <section className="card statement-upload statement-csv">
  <h2>{w.title}</h2><p>{w.help}</p>{error&&<div className="error" role="alert">{error}</div>}
  <div className="form-grid">
   <label className="span2">{w.file}<input ref={input} type="file" accept=".csv,text/csv" disabled={busy} onChange={e=>{setFile(e.target.files?.[0]||null);setDelimiter('');setEncoding('auto');setHeader(0);invalidate()}}/></label>
   <label>{w.delimiter}<select value={delimiter} disabled={busy} onChange={e=>{setDelimiter(e.target.value);invalidate()}}><option value="">{w.auto}</option><option value=";">;</option><option value=",">,</option><option value={'\t'}>{w.tab}</option><option value="|">|</option></select></label>
   <label>{w.encoding}<select value={encoding} disabled={busy} onChange={e=>{setEncoding(e.target.value);invalidate()}}><option value="auto">{w.auto}</option><option value="utf-8-sig">UTF-8</option><option value="cp1252">Windows-1252</option></select></label>
   <label>{w.header}<input type="number" min="0" max="30" value={header} disabled={busy} onChange={e=>{setHeader(Number(e.target.value));invalidate()}}/></label>
  </div>
  <button className="secondary" disabled={!file||busy} onClick={load}>{busy?<LoaderCircle size={17} className="spin"/>:<FileSpreadsheet size={17}/>} {w.preview}</button>
  {preview&&<>
   <p className="statement-csv-help">{preview.row_count} {w.rows} · {w.columnsHelp}</p>
   <div className="statement-csv-preview"><table><thead><tr><th>{w.line}</th>{preview.columns.map((c,i)=><th key={i}>{c}</th>)}</tr></thead><tbody>{preview.sample.map(row=><tr key={row.line}><td>{row.line}</td>{preview.columns.map((_,i)=><td key={i}>{row.cells[i]||'–'}</td>)}</tr>)}</tbody></table></div>
   <fieldset disabled={busy}><div className="form-grid">
    {(['date','merchant','amount','debit','credit','currency','entry_type','reference'] as const).map(key=><label key={key}>{w[key]}<select value={mapping[key]??''} onChange={e=>{setMapping(old=>({...old,[key]:e.target.value===''?null:Number(e.target.value)}));setConfirmed(false)}}><option value="">{w.unused}</option>{preview.columns.map((name,index)=><option value={index} key={index}>{index+1} · {name}</option>)}</select></label>)}
    <label>{w.dateFormat}<select value={format} onChange={e=>{setFormat(e.target.value);setConfirmed(false)}}><option value="auto">{w.auto} (ISO / DE)</option><option value="dmy">{w.dmy}</option><option value="mdy">{w.mdy}</option><option value="iso">{w.iso}</option></select></label>
    <label>{w.direction}<select value={direction} onChange={e=>{setDirection(e.target.value);setConfirmed(false)}}><option value="signed">{w.signed}</option><option value="expense">{w.expense}</option><option value="income">{w.income}</option></select></label>
    <label>{w.account}<select value={account} onChange={e=>setAccount(e.target.value)}><option value="">{w.later}</option>{accounts.map(a=><option value={a.id} key={a.id}>{a.name}</option>)}</select></label>
   </div><label className="check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>{w.confirm}</label></fieldset>
   <div className="statement-upload-actions"><span/>{<button disabled={!valid||!confirmed||busy} onClick={start}>{busy&&<LoaderCircle className="spin" size={17}/>} {w.import}</button>}</div>
  </>}
 </section>
}
