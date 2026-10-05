(() => {
const source=()=>window.chrome?.webview?'?source=game&activeClub='+encodeURIComponent(sessionStorage.getItem('ff-live-club')||'0'):'';
const modelRequests=new Map();
const cache=new Map(),endpoint='http://127.0.0.1:8876';
async function load(id,onUpdate){const key=String(id);if(cache.has(key))onUpdate(cache.get(key));for(let attempt=0;attempt<150;attempt++){const response=await fetch(endpoint+'/api/clubs/'+encodeURIComponent(id)+source());if(!response.ok)throw new Error('Não foi possível ler o clube no save.');const payload=await response.json();if(payload.error)throw new Error(payload.error);if(payload.detail){cache.set(key,payload.detail);onUpdate(payload.detail,payload.renderPending);}if(!payload.renderPending)return payload.detail;await new Promise(resolve=>setTimeout(resolve,1800));}throw new Error('A geração das imagens ainda está em andamento.');}
async function pose(club,player,pose){const response=await fetch(endpoint+'/api/players/'+club+'/'+player+'/'+pose+source());const data=await response.json();if(!response.ok)throw new Error(data.error||'Modelo indisponível');return data.image;}
async function model(club,player,pose){const url=endpoint+'/api/models/'+club+'/'+player+'/'+pose+source();if(modelRequests.has(url))return modelRequests.get(url);const pending=(async()=>{const response=await fetch(url);const data=await response.json();if(!response.ok)throw new Error(data.error||'Modelo indisponível');return data.image;})();modelRequests.set(url,pending);try{return await pending;}finally{modelRequests.delete(url);}}
async function metadata(id){const response=await fetch(endpoint+'/api/clubs/'+encodeURIComponent(id)+'?metadata=1'+(window.chrome?.webview?source().replace('?','&'):''));if(!response.ok)throw new Error('Clube indisponível');return (await response.json()).detail;}
async function team(club,mode,pose){const response=await fetch(endpoint+'/api/teams/'+club+'/'+mode+'/'+pose+source());const data=await response.json();if(!response.ok)throw new Error(data.error||'Cena indisponível');return data.image;}
window.FFClubData={load,pose,model,metadata,team};
})();
