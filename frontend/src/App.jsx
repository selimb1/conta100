
import React, { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const tabs = ["Clientes","Documentos","Previsualización","Resultados","Configuración"];

export default function App(){
  const [tab, setTab] = useState(tabs[0]);
  return (
    <div style={{fontFamily:"system-ui, Inter, Arial", padding:20}}>
      <h1>Conta — MVP</h1>
      <nav style={{display:"flex", gap:10, marginBottom:20}}>
        {tabs.map(t => (
          <button key={t} onClick={()=>setTab(t)} style={{padding:"8px 12px", borderRadius:8, border: "1px solid #ddd", background: tab===t?"#eee":"#fff"}}>{t}</button>
        ))}
      </nav>
      {tab==="Clientes" && <Clientes/>}
      {tab==="Documentos" && <Documentos/>}
      {tab==="Previsualización" && <Previsualizacion/>}
      {tab==="Resultados" && <Resultados/>}
      {tab==="Configuración" && <Config/>}
    </div>
  )
}

function Clientes(){
  const [list,setList]=useState([]);
  const [form,setForm]=useState({nombre:"", cuit:"", condicion_fiscal:"Responsable Inscripto"});
  const reload=async()=>{ const {data}=await axios.get(API+"/clientes"); setList(data) }
  useEffect(()=>{reload()},[]);
  const crear=async(e)=>{e.preventDefault(); await axios.post(API+"/clientes", form); setForm({nombre:"",cuit:"",condicion_fiscal:"Responsable Inscripto"}); reload();}
  const del_=async(id)=>{ await axios.delete(API+`/clientes/${id}`); reload(); }
  return (<div>
    <h2>Alta de cliente</h2>
    <form onSubmit={crear} style={{display:"grid", gap:8, maxWidth:420}}>
      <input placeholder="Nombre" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})}/>
      <input placeholder="CUIT (xx-xxxxxxxx-x)" value={form.cuit} onChange={e=>setForm({...form,cuit:e.target.value})}/>
      <select value={form.condicion_fiscal} onChange={e=>setForm({...form,condicion_fiscal:e.target.value})}>
        <option>Monotributista</option>
        <option>Responsable Inscripto</option>
      </select>
      <button>Crear</button>
    </form>
    <h3>Clientes</h3>
    <table border="1" cellPadding="6"><thead><tr><th>ID</th><th>Nombre</th><th>CUIT</th><th>Condición</th><th></th></tr></thead>
      <tbody>
        {list.map(c=>(<tr key={c.id}><td>{c.id}</td><td>{c.nombre}</td><td>{c.cuit}</td><td>{c.condicion_fiscal}</td>
        <td><button onClick={()=>del_(c.id)}>Eliminar</button></td></tr>))}
      </tbody>
    </table>
  </div>)
}

function Documentos(){
  const [clientes,setClientes]=useState([]); const [clienteId,setClienteId]=useState("");
  const [tipo,setTipo]=useState("Factura");
  const [file,setFile]=useState(null);
  useEffect(()=>{ axios.get(API+"/clientes").then(r=>setClientes(r.data)) },[])
  const subir=async(e)=>{ e.preventDefault(); const fd=new FormData(); fd.append("cliente_id", clienteId); fd.append("tipo", tipo); fd.append("file", file); await axios.post(API+"/documentos/upload", fd, {headers:{'Content-Type':'multipart/form-data'}}); alert("Subido"); }
  return (<div>
    <h2>Subir documentos</h2>
    <form onSubmit={subir} style={{display:"grid", gap:8, maxWidth:420}}>
      <select value={clienteId} onChange={e=>setClienteId(e.target.value)}>
        <option value="">Seleccione cliente</option>
        {clientes.map(c=><option key={c.id} value={c.id}>{c.nombre} ({c.cuit})</option>)}
      </select>
      <input value={tipo} onChange={e=>setTipo(e.target.value)} placeholder="Tipo (Factura, NC, ND, Recibo, etc.)"/>
      <input type="file" onChange={e=>setFile(e.target.files[0])}/>
      <button disabled={!file || !clienteId}>Subir</button>
    </form>
  </div>)
}

function Previsualizacion(){
  const [clienteId,setClienteId]=useState("");
  const [clientes,setClientes]=useState([]); const [data,setData]=useState(null);
  useEffect(()=>{ axios.get(API+"/clientes").then(r=>setClientes(r.data)) },[])
  const procesar=async()=>{ const {data}=await axios.post(API+"/procesar", {cliente_id:Number(clienteId)}); setData(data.contenido_json); }
  return (<div>
    <h2>Previsualización</h2>
    <select value={clienteId} onChange={e=>setClienteId(e.target.value)}>
      <option value="">Seleccione cliente</option>
      {clientes.map(c=><option key={c.id} value={c.id}>{c.nombre}</option>)}
    </select>
    <button onClick={procesar} disabled={!clienteId}>Procesar</button>
    {data && <div style={{marginTop:16}}>
      <h3>Asientos (preview)</h3>
      <table border="1" cellPadding="4"><thead><tr><th>Fecha</th><th>Cuenta</th><th>Debe</th><th>Haber</th><th>Detalle</th></tr></thead>
        <tbody>{data.asientos.map((a,i)=><tr key={i}><td>{a.Fecha}</td><td>{a.Cuenta}</td><td>{a.Debe}</td><td>{a.Haber}</td><td>{a.Detalle||""}</td></tr>)}</tbody>
      </table>
      <p>Cuadre de sumas: {String(data._validaciones.cuadre_sumas)}</p>
    </div>}
  </div>)
}

function Resultados(){
  const [clienteId,setClienteId]=useState("");
  const [clientes,setClientes]=useState([]);
  useEffect(()=>{ axios.get(API+"/clientes").then(r=>setClientes(r.data)) },[])
  const descargar=(tipo)=>{ window.open(`${API}/exportar/${tipo}?cliente_id=${clienteId}`,'_blank'); }
  const descargarTodo=()=>{ window.open(`${API}/exportar_zip?cliente_id=${clienteId}`,'_blank'); }
  const tipos=["asientos","mayor","balance_ss","ee_pp","ee_rr","ee_pn","flujo","iva","ganancias","iibb","bbpp","libro_iva","sueldos"];
  return (<div>
    <h2>Resultados</h2>
    <select value={clienteId} onChange={e=>setClienteId(e.target.value)}>
      <option value="">Seleccione cliente</option>
      {clientes.map(c=><option key={c.id} value={c.id}>{c.nombre}</option>)}
    </select>
    <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(160px,1fr))", gap:10, marginTop:10}}>
      {tipos.map(t=><button key={t} onClick={()=>descargar(t)} disabled={!clienteId}>Descargar {t}</button>)}
    </div>
    <button style={{marginTop:12}} onClick={descargarTodo} disabled={!clienteId}>Descargar todo (.zip)</button>
    <h3 style={{marginTop:20}}>Descargar archivos AFIP (.txt)</h3>
<div style={{display:"flex", gap:10, flexWrap:"wrap"}}>
  {["iva","ganancias","iibb","bbpp"].map(t=>(
    <button key={t} 
      onClick={()=>window.open(`${API}/exportar_afip/${t}?cliente_id=${clienteId}`,'_blank')} 
      disabled={!clienteId}>
      {t.toUpperCase()}
    </button>
  ))}
</div>

  </div>)
}

function Config(){
  const [api,setApi]=useState(API);
  return (<div>
    <h2>Configuración</h2>
    <p>API: {api}</p>
    <p>Defina VITE_API_URL en frontend/.env para apuntar a otra URL.</p>
  </div>)
}
