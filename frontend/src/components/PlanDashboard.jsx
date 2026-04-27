import React, {useEffect, useState, useRef} from 'react';

export default function PlanDashboard(){
  const [plans, setPlans] = useState([])
  const [pending, setPending] = useState([])
  const [selected, setSelected] = useState(null)
  const [details, setDetails] = useState(null)
  const pollRef = useRef(null)

  useEffect(()=>{
    fetch('/api/plans').then(r=>r.json()).then(d=>setPlans(d.plans || []))
    fetch('/api/plans/pending_approvals').then(r=>r.json()).then(d=>setPending(d.pending || []))
  },[])

  useEffect(()=>{
    if(!selected) {
      setDetails(null)
      if(pollRef.current){ clearInterval(pollRef.current); pollRef.current = null }
      return
    }

    // Prefer SSE for live updates when available
    let es = null
    let polling = null

    const fetchProgressOnce = async () => {
      try {
        const res = await fetch(`/api/plans/${selected}/progress`)
        if(res.ok){
          const json = await res.json()
          setDetails(json)
          return true
        }
      } catch(err) {
        // fallthrough
      }
      return false
    }

    const startPolling = () => {
      if(pollRef.current) return
      pollRef.current = setInterval(async ()=>{
        await fetchProgressOnce()
      }, 2000)
    }

    const startSSE = () => {
      try {
        if (typeof EventSource === 'undefined') return false
        es = new EventSource(`/api/plans/${selected}/stream`)
        es.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data)
            setDetails(data)
          } catch(e) {
            // ignore malformed
          }
        }
        es.onerror = () => {
          try { es.close() } catch(e){}
          es = null
          // fallback to polling
          startPolling()
        }
        return true
      } catch (e) {
        return false
      }
    }

    (async ()=>{
      const ok = await fetchProgressOnce()
      // Try SSE; if not available start polling
      if(!startSSE()) startPolling()
    })()

    return ()=>{
      if(es){ try{ es.close() }catch(e){} }
      if(pollRef.current){ clearInterval(pollRef.current); pollRef.current = null }
    }
  },[selected])

  async function doApprove(planId){
    const approved_by = prompt('Your name for approval (optional)', 'user')
    if(approved_by === null) return
    const message = prompt('Approval message (optional)', '') || ''
    try{
      const res = await fetch(`/api/plans/${encodeURIComponent(planId)}/approve`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({approved_by, message})})
      if(res.ok){
        alert('Approved')
        // refresh pending list
        fetch('/api/plans/pending_approvals').then(r=>r.json()).then(d=>setPending(d.pending || []))
        // refresh plan details if currently viewing
        if(selected === planId){ fetch(`/api/plans/${selected}/progress`).then(r=>r.json()).then(d=>setDetails(d)) }
        // refresh audit trail component by dispatching a custom event
        try{ window.dispatchEvent(new Event('audit-refresh')) }catch(e){}
      } else {
        const txt = await res.text()
        alert('Approval failed: ' + txt)
      }
    } catch(e){
      alert('Approval error')
    }
  }

  // Inline AuditTrail component
  function AuditTrail(){
    const [approvals, setApprovals] = useState([])
    const [expanded, setExpanded] = useState({})
    useEffect(()=>{
      const load = ()=>fetch('/api/plans/approvals').then(r=>r.json()).then(d=>setApprovals(d.approvals || []))
      load()
      const onRefresh = ()=>load()
      window.addEventListener('audit-refresh', onRefresh)
      return ()=> window.removeEventListener('audit-refresh', onRefresh)
    },[])

    if(!approvals.length) return <div style={{fontSize:13,color:'#555'}}>No approvals yet</div>
    return (
      <div>
        {approvals.map((a,idx)=> (
          <div key={idx} style={{padding:8,borderBottom:'1px solid #eee'}}>
            <div style={{fontSize:13}}><strong>{a.task || a.plan_id}</strong></div>
            <div style={{fontSize:12,color:'#666'}}>{a.approved_by} @ {a.approved_at}</div>
            <div style={{marginTop:6}}>
              <button onClick={()=> setExpanded((s)=>({ ...s, [idx]: !s[idx]})) } style={{marginRight:8}}>{expanded[idx] ? 'Hide' : 'Show'}</button>
            </div>
            {expanded[idx] ? (
              <div style={{marginTop:8}}>
                <div><strong>Message:</strong> {a.approved_message || ''}</div>
                <div><strong>Staged diffs:</strong></div>
                {(a.staged_diffs || []).map((d,di)=> (
                  <div key={di} style={{marginTop:6,background:'#fafafa',padding:8,border:'1px solid #eee',display:'flex',flexDirection:'column'}}>
                    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                      <div style={{fontSize:12}}><strong>{d.path}</strong></div>
                      <div>
                        <label style={{fontSize:12}}>
                          <input type="checkbox" defaultChecked onChange={(e)=>{
                            setApprovals(prev=>{
                              const cur = prev || {}
                              const arr = (cur[a.plan_id] || [] ).slice()
                              if(e.target.checked){
                                if(!arr.includes(d.path)) arr.push(d.path)
                              } else {
                                const idx = arr.indexOf(d.path)
                                if(idx>=0) arr.splice(idx,1)
                              }
                              return { ...cur, [a.plan_id]: arr }
                            })
                          }} /> Accept
                        </label>
                      </div>
                    </div>
                    <pre style={{whiteSpace:'pre-wrap',fontSize:12,background:'#fff',marginTop:8}}>{d.diff || '(no diff)'}</pre>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    )
  }
              </div>
            ) : null}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="plan-dashboard">
      <aside style={{width:320,float:'left',padding:12,borderRight:'1px solid #ddd'}}>
        <h3>Pending Approvals</h3>
        <ul>
          {pending.length === 0 ? <li><em>No pending approvals</em></li> : pending.map(p=> (
            <li key={p.plan_id} style={{marginBottom:8}}>
              <div><strong>{p.task || p.plan_id}</strong></div>
              <div style={{fontSize:12,color:'#555'}}>Step {p.step_number}: {p.step_description}</div>
              <div style={{marginTop:6}}>
                <button onClick={()=>{ setSelected(p.plan_id); window.scrollTo(0,0) }} style={{marginRight:8}}>View</button>
                <button onClick={()=>doApprove(p.plan_id)} className="primary">Approve</button>
              </div>
            </li>
          ))}
        </ul>

        <hr />
        <h3>Saved Plans</h3>
        <ul>
          {plans.map(p=> (
            <li key={p}><button onClick={()=>setSelected(p)} style={{background:'none',border:0,color:'#06c',cursor:'pointer'}}>{p}</button></li>
          ))}
        </ul>

        <hr />
        <h3>Audit Trail</h3>
        <ul>
          <AuditTrail />
        </ul>
        <ul>
          {plans.map(p=> (
            <li key={p}><button onClick={()=>setSelected(p)} style={{background:'none',border:0,color:'#06c',cursor:'pointer'}}>{p}</button></li>
          ))}
        </ul>
      </aside>
      <main style={{marginLeft:340,padding:12}}>
        <h2>Plan Details</h2>
        {details ? (
          <div>
            <p><strong>Task:</strong> {details.task}</p>
            <p><strong>Status:</strong> {details.status} — <strong>Progress:</strong> {details.progress}</p>
            <h4>Steps</h4>
            <ol>
              {(details.steps||[]).map((s,idx)=>(
                <li key={idx}>
                  <strong>{s.step_number}.</strong> {s.description} — <em>{s.status}</em>
                  {s.metadata && s.metadata.requires_approval ? (
                    <div style={{marginTop:6,padding:8,background:'#fff8e1',border:'1px solid #ffe0b2'}}>
                      <div><strong>Requires approval</strong></div>
                      <div style={{fontSize:13,marginTop:6}}>
                        Suggested sub-steps:
                        <pre style={{whiteSpace:'pre-wrap',background:'#fafafa',padding:8}}>{JSON.stringify(s.metadata.suggested_substeps || [], null, 2)}</pre>
                        <button onClick={()=>doApprove(details.plan_id)} className="primary">Approve and resume</button>
                      </div>
                    </div>
                  ) : null}
                </li>
              ))}
            </ol>
            <pre style={{whiteSpace:'pre-wrap',background:'#f7f7f7',padding:12}}>{JSON.stringify(details,null,2)}</pre>
          </div>
        ) : (<p>Select a plan to view details</p>)}
      </main>
    </div>
  )
}
