import {useEffect,useMemo,useState} from 'react';

export default function ProviderIcon({provider,website,name,size=30}:{provider?:string|null;website?:string|null;name?:string|null;size?:number}){
  const[url,setUrl]=useState<string|null>(null);
  const fallback=useMemo(()=>((provider||name||'?').trim()[0]||'?').toUpperCase(),[provider,name]);
  useEffect(()=>{
    let active=true;const value=(provider||'').trim();const site=(website||'').trim();
    if(!value&&!site){setUrl(null);return()=>{active=false}}
    const timer=setTimeout(()=>{
      fetch(`/api/provider-icons/resolve?provider=${encodeURIComponent(value)}&website=${encodeURIComponent(site)}`,{credentials:'include'})
        .then(r=>r.ok?r.json():null).then(x=>{if(active)setUrl(x?.url||null)}).catch(()=>{if(active)setUrl(null)})
    },180);
    return()=>{active=false;clearTimeout(timer)};
  },[provider,website]);
  return <span className="provider-icon" style={{width:size,height:size}} aria-hidden="true">{url?<img src={url} alt=""/>:<b>{fallback}</b>}</span>
}
