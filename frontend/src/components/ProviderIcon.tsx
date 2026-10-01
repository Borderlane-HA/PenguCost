import {useEffect,useMemo,useState} from 'react';

export default function ProviderIcon({provider,website,name,size=30}:{provider?:string|null;website?:string|null;name?:string|null;size?:number}){
  const[url,setUrl]=useState<string|null>(null);
  const fallback=useMemo(()=>((provider||name||'?').trim()[0]||'?').toUpperCase(),[provider,name]);
  useEffect(()=>{
    let active=true;const value=(provider||'').trim();const site=(website||'').trim();const timers:number[]=[];
    if(!value&&!site){setUrl(null);return()=>{active=false}}
    const resolve=()=>fetch(`/api/provider-icons/resolve?provider=${encodeURIComponent(value)}&website=${encodeURIComponent(site)}`,{credentials:'include'})
      .then(r=>r.ok?r.json():null).then(x=>{if(!active)return true;if(x?.url){setUrl(`${x.url}?v=${x.mtime||''}`);return true}setUrl(null);return false}).catch(()=>{if(active)setUrl(null);return false});
    timers.push(window.setTimeout(()=>{resolve().then(found=>{if(found||!active)return;timers.push(window.setTimeout(()=>resolve().then(foundAgain=>{if(!foundAgain&&active)timers.push(window.setTimeout(resolve,2200))}),1200))})},120));
    return()=>{active=false;timers.forEach(window.clearTimeout)};
  },[provider,website]);
  return <span className={`provider-icon ${url?'has-image':'fallback'}`} style={{width:size,height:size}} aria-hidden="true">{url?<img src={url} alt=""/>:<b>{fallback}</b>}</span>
}
