code = '''import React, { useState, useEffect, useRef } from 'react';

export default function App() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [intents, setIntents] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [answer, setAnswer] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  
  // Pipeline state
  const [transcript, setTranscript] = useState('');
  const [controllerDecision, setControllerDecision] = useState<any>(null);

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws/demo_session');
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEvents((prev) => [...prev, data]);
      
      const ts = new Date().toISOString().split('T')[1].slice(0, 12);
      
      if (data.event === 'controller_decision') {
        setControllerDecision(data);
        setTranscript(data.text);
        setTimeline(prev => [...prev, {ts, msg: 'CONTROLLER_' + data.decision, detail: data.reason}]);
      }
      if (data.event === 'intents_extracted') {
        setIntents(data.intents);
        setTimeline(prev => [...prev, {ts, msg: 'INTENTS_EXTRACTED', detail: data.intents.length + ' intents'}]);
      }
      if (data.event === 'answer_generated') {
        setAnswer(data.answer);
        setEvidence(data.evidence);
        setVersions(prev => [...prev, data.answer]);
        setTimeline(prev => [...prev, {ts, msg: 'ANSWER_V' + data.answer.version, detail: 'Supported claims: ' + data.answer.supported_claims}]);
      }
    };
    setWs(socket);
    return () => socket.close();
  }, []);

  const runDemo = async () => {
    if (!ws) return;
    setEvents([]); setIntents([]); setEvidence([]); setAnswer(null); setVersions([]); setTimeline([]); setTranscript(''); setControllerDecision(null);
    
    setTimeline([{ts: new Date().toISOString().split('T')[1].slice(0, 12), msg: 'SYSTEM_READY', detail: 'Running canonical scenario'}]);
    
    const turn1 = "I need to find the requirements for a customer workshop in Pune and also tell me the cancellation policy.";
    const words1 = turn1.split(" ");
    
    let buf = "";
    for (let i = 0; i < words1.length; i++) {
      buf += words1[i] + " ";
      ws.send(JSON.stringify({ type: 'chunk', seq: i, t_ms: i * 200, text: buf.trim(), is_final: i === words1.length - 1 }));
      await new Promise(r => setTimeout(r, 200));
    }
    
    await new Promise(r => setTimeout(r, 1500));
    
    const turn2 = "Actually make the workshop location Delhi.";
    const words2 = turn2.split(" ");
    buf = turn1 + "\\n\\n";
    for (let i = 0; i < words2.length; i++) {
      buf += words2[i] + " ";
      ws.send(JSON.stringify({ type: 'chunk', seq: i + words1.length, t_ms: (i + words1.length) * 200, text: buf.trim(), is_final: i === words2.length - 1 }));
      await new Promise(r => setTimeout(r, 200));
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-8 font-mono">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* HEADER */}
        <header className="border-b border-slate-800 pb-6 flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-bold text-white tracking-tight mb-2">STREAMING LIVE RAG</h1>
            <p className="text-slate-400">Samsung PRISM Theme 4 - Final Audit</p>
          </div>
          <div className="flex gap-4">
             <div className="text-right">
                <div className="text-xs text-slate-500 uppercase">Architecture</div>
                <div className="text-sm text-emerald-400 font-semibold">Event-Driven Pipeline</div>
             </div>
             <button onClick={runDemo} className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 rounded font-bold transition-colors">
               Run Demo Scenario
             </button>
          </div>
        </header>

        <div className="grid grid-cols-12 gap-8">
          
          {/* LEFT: PIPELINE VIZ */}
          <div className="col-span-8 space-y-6">
            
            <section className="bg-slate-900 border border-slate-800 rounded p-6">
              <h2 className="text-sm font-bold text-slate-500 uppercase mb-4 tracking-widest">1. Transcript Buffer</h2>
              <div className="text-lg text-white font-sans min-h-[4rem] bg-slate-950 p-4 rounded border border-slate-800">
                {transcript || <span className="text-slate-600">Waiting for stream...</span>}
              </div>
            </section>

            <div className="grid grid-cols-2 gap-6">
              <section className="bg-slate-900 border border-slate-800 rounded p-6">
                <h2 className="text-sm font-bold text-slate-500 uppercase mb-4 tracking-widest">2. Controller</h2>
                <div className="flex items-center gap-4">
                  <div className={px-4 py-2 rounded font-bold \}>
                    {controllerDecision?.decision || 'IDLE'}
                  </div>
                  <div className="text-sm text-slate-400">{controllerDecision?.reason}</div>
                </div>
              </section>

              <section className="bg-slate-900 border border-slate-800 rounded p-6">
                <h2 className="text-sm font-bold text-slate-500 uppercase mb-4 tracking-widest">3. Intent Delta</h2>
                <div className="space-y-2">
                  {intents.length === 0 && <span className="text-slate-600 text-sm">No intents extracted yet</span>}
                  {intents.map((intent, i) => (
                    <div key={i} className="bg-slate-950 border border-slate-800 p-3 rounded">
                      <div className="text-white text-sm">{intent.description}</div>
                      <div className="flex gap-2 mt-2">
                        {intent.constraints.map((c: any, j: number) => (
                          <span key={j} className="text-xs px-2 py-1 bg-blue-900/50 text-blue-300 rounded">
                            {c.key}: {c.value}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <section className="bg-slate-900 border border-slate-800 rounded p-6">
              <h2 className="text-sm font-bold text-slate-500 uppercase mb-4 tracking-widest">4. Evidence Base</h2>
              <div className="space-y-3">
                 {evidence.length === 0 && <span className="text-slate-600 text-sm">No evidence retrieved</span>}
                 {evidence.map((ev, i) => (
                   <div key={i} className="bg-slate-950 border border-slate-800 p-4 rounded hover:border-slate-600 transition-colors cursor-pointer group">
                     <div className="flex justify-between items-start mb-2">
                       <span className="text-xs font-bold text-emerald-400">{ev.document_id} :: {ev.section_id}</span>
                       <span className="text-xs text-slate-500">{ev.chunk_id}</span>
                     </div>
                     <p className="text-sm text-slate-300 group-hover:text-white transition-colors">{ev.text}</p>
                   </div>
                 ))}
              </div>
            </section>
            
            <section className="bg-slate-900 border border-slate-800 rounded p-6">
              <h2 className="text-sm font-bold text-slate-500 uppercase mb-4 tracking-widest">5. Grounded Versions</h2>
              <div className="space-y-6">
                {versions.length === 0 && <span className="text-slate-600 text-sm">No versions generated</span>}
                {versions.map((v, i) => (
                  <div key={i} className="border border-slate-800 rounded p-5 bg-slate-950 relative overflow-hidden">
                    <div className="absolute top-0 right-0 bg-slate-800 text-xs px-3 py-1 font-bold text-slate-300 rounded-bl">V{v.version}</div>
                    
                    {v.delta_summary && (
                      <div className="mb-4 text-xs">
                        <span className="text-slate-500 block mb-1">Delta Execution:</span>
                        <div className="flex gap-3">
                          <span className="text-emerald-400">Affected: {v.delta_summary.affected_intents?.length || 0}</span>
                          <span className="text-blue-400">Preserved: {v.delta_summary.preserved_intents?.length || 0}</span>
                          <span className="text-amber-400">Changed Constraints: {v.delta_summary.changed_constraints?.length || 0}</span>
                        </div>
                      </div>
                    )}
                    
                    <div className="space-y-3">
                       {v.claims.map((claim: any, j: number) => (
                         <div key={j} className="border-l-2 border-slate-700 pl-4 py-1">
                           <div className="text-white text-sm mb-1">{claim.text}</div>
                           <div className="flex items-center gap-3 text-xs">
                             <span className={\ont-bold \\}>
                               {claim.status}
                             </span>
                             <span className="text-slate-500">{claim.verification_reason}</span>
                             {claim.citations && claim.citations.map((cit: any, k: number) => (
                               <span key={k} className="bg-slate-800 px-2 rounded text-slate-300">{cit.display}</span>
                             ))}
                           </div>
                         </div>
                       ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

          </div>

          {/* RIGHT: TELEMETRY TIMELINE */}
          <div className="col-span-4">
             <div className="bg-slate-900 border border-slate-800 rounded p-6 sticky top-8">
               <h2 className="text-sm font-bold text-slate-500 uppercase mb-4 tracking-widest">Telemetry Timeline</h2>
               <div className="space-y-4 max-h-[80vh] overflow-y-auto pr-2">
                 {timeline.length === 0 && <span className="text-slate-600 text-sm">System idle</span>}
                 {timeline.map((item, i) => (
                   <div key={i} className="flex gap-3 text-sm">
                     <span className="text-slate-500 whitespace-nowrap">{item.ts}</span>
                     <div>
                       <div className="text-emerald-400 font-bold">{item.msg}</div>
                       {item.detail && <div className="text-slate-400 text-xs mt-0.5">{item.detail}</div>}
                     </div>
                   </div>
                 ))}
               </div>
             </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
'''
with open('frontend/src/App.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
