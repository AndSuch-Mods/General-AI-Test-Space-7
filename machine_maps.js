// Per-machine Kepware maps. DB numbers and notes never copy between machines.
function renderMap(){
  for(const machine of ['MM4','MM5','MM6']){
    const box=$('#'+(machine==='MM6'?'tag-map':'tag-map-'+machine));
    if(!box)continue;
    const savedDb=state.fields[machine]?.reportDbCompact||'';
    const reservedDb=machine==='MM6'?'56':((machine==='MM4'||machine==='MM5')?'66':'');
    const db=savedDb||reservedDb;
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
    box.append(e('p','muted',machine==='MM6'?'MM6 is field-confirmed as CSI_Report_MM6 [DB56]. The TIA absolute address and Kepware item address are both shown below.':((machine==='MM4'||machine==='MM5')?'DB66 is reserved for '+report+' after the project-wide DB66 search returned no matches on this machine. Create the report DB as DB66; if TIA later shows DB66 occupied, stop and change the reservation before downloading.':'Enter this machine’s confirmed reporting DB number.')));
    const wrap=e('div','table-wrap'),tab=e('table'),head=e('thead'),tr=e('tr');
    ['Tag','Type','Byte','TIA absolute','Kepware item'].forEach(v=>tr.append(e('th','',v)));head.append(tr);tab.append(head);
    const body=e('tbody');
    for(const f of DATA.schema){
      const row=e('tr');row.append(e('td','',f.name),e('td','',f.kepware_type),e('td','',String(f.offset)));
      const tia=e('td','address'),kep=e('td','address');
      tia.append(e('code','',valid?('%DB'+Number(db)+'.DBD'+f.offset):'Enter DB number'));
      kep.append(e('code','',valid?('DB'+Number(db)+','+f.type.toUpperCase()+f.offset):'Enter DB number'));
      row.append(tia,kep);body.append(row);
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
