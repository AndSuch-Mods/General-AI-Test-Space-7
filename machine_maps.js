// Per-machine Kepware maps. DB numbers and notes never copy between machines.
function renderMap(){
  for(const machine of ['MM4','MM5','MM6']){
    const box=$('#'+(machine==='MM6'?'tag-map':'tag-map-'+machine));
    if(!box)continue;
    const db=state.fields[machine]?.reportDbCompact||'';
    const valid=/^[0-9]+$/.test(db)&&Number(db)>=1&&Number(db)<=65535;
    const report='CSI_Report_'+machine;
    box.replaceChildren();
    const label=e('label','field',report+' DB number (enter it, then press Tab)');
    const input=e('input');input.type='number';input.min='1';input.max='65535';input.value=db;
    input.id=machine==='MM6'?'kepware-db':'kepware-db-'+machine;
    label.append(input);box.append(label);
    input.addEventListener('change',()=>{
      state.fields[machine]??={};state.fields[machine].reportDbCompact=input.value;
      const other=$('#field-'+machine+'-reportDbCompact');if(other)other.value=input.value;
      save();renderMap();
    });
    box.append(e('p','muted',valid?'Verify the offsets in '+report+' on '+machine+'.':'Enter this machine’s confirmed reporting DB number. A different machine’s number is not reused.'));
    const wrap=e('div','table-wrap'),tab=e('table'),head=e('thead'),tr=e('tr');
    ['Tag','Type','Byte','Kepware address'].forEach(v=>tr.append(e('th','',v)));head.append(tr);tab.append(head);
    const body=e('tbody');
    for(const f of DATA.schema){
      const row=e('tr');row.append(e('td','',f.name),e('td','',f.kepware_type),e('td','',String(f.offset)));
      const cell=e('td','address');cell.append(e('code','',valid?`DB${Number(db)},${f.type.toUpperCase()}${f.offset}`:'Enter DB number'));row.append(cell);body.append(row);
    }
    tab.append(body);wrap.append(tab);box.append(wrap);
    const button=e('button','small-button','Download complete address reference');button.disabled=!valid;
    button.onclick=()=>{
      const rows=[['Machine','Tag','Address','Type','Client access','Meaning'],...DATA.schema.map(f=>[machine,f.name,`DB${Number(db)},${f.type.toUpperCase()}${f.offset}`,f.kepware_type,'Read Only',f.description])];
      download(report+'_DB'+Number(db)+'_reference.csv',rows.map(r=>r.map(x=>'"'+String(x).replaceAll('"','""')+'"').join(',')).join('\r\n'),'text/csv;charset=utf-8');
    };
    box.append(button,e('p','muted','Create these under the '+machine+' device, for example Siemens.'+machine+'.Production.DayShiftCurrent. Use the actual channel name. Reference CSV only; all time values are REAL seconds.'));
  }
}
