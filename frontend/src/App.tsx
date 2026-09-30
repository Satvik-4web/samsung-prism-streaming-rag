import React, { useState, useEffect, useRef } from 'react';

export default function App() {
  const [transcript, setTranscript] = useState('');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [intents, setIntents] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [answer, setAnswer] = useState<any>(null);
  
  const [versions, setVersions] = useState<any[]>([]);

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws/demo_session');
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEvents((prev) => [...prev, data]);
      if (data.event === 'intents_extracted') {
        setIntents(data.intents);
      }
      if (data.event === 'answer_generated') {
        setAnswer(data.answer);
        setEvidence(data.evidence);
        setVersions(prev => [...prev, data.answer]);
      }
    };
    setWs(socket);
    return () => socket.close();
  }, []);

  const sendChunk = (text: string, isFinal: boolean = false) => {
    if (ws) {
      ws.send(JSON.stringify({
        type: 'chunk',
        text: text,
        seq: Date.now(),
        t_ms: Date.now(),
        is_final: isFinal
      }));
    }
  };

  const handleSimulate = async () => {
    setEvents([]); setIntents([]); setEvidence([]); setAnswer(null); setVersions([]);
    await fetch('http://localhost:8000/session/demo_session/reset', { method: 'POST' });
    
    // Simulate streaming
    const query1 = "I need to plan a customer workshop in Pune and what is the cancellation policy?";
    const words = query1.split(' ');
    let buf = '';
    for (let i = 0; i < words.length; i++) {
      buf += words[i] + ' ';
      setTranscript(buf);
      sendChunk(buf, i === words.length - 1);
      await new Promise(r => setTimeout(r, 300));
    }
    
    await new Promise(r => setTimeout(r, 2000));
    
    // Delta constraint
    const query2 = "Actually make the workshop location Delhi.";
    let buf2 = '';
    const words2 = query2.split(' ');
    for (let i = 0; i < words2.length; i++) {
      buf2 += words2[i] + ' ';
      setTranscript(query1 + '\n\n' + buf2);
      sendChunk(query1 + ' ' + buf2, i === words2.length - 1);
      await new Promise(r => setTimeout(r, 300));
    }
  };

  return (
    <div className="p-4 max-w-6xl mx-auto grid grid-cols-3 gap-4 font-sans text-sm">
      <div className="col-span-3 mb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold">Theme 4: Streaming Live RAG</h1>
        <button onClick={handleSimulate} className="bg-blue-600 text-white px-4 py-2 rounded">
          Run Demo Scenario
        </button>
      </div>

      <div className="border p-4 bg-white shadow rounded">
        <h2 className="font-bold mb-2 border-b pb-1">1. Live Transcript</h2>
        <div className="whitespace-pre-wrap bg-gray-100 p-2 min-h-32 font-mono text-xs">{transcript}</div>
      </div>

      <div className="border p-4 bg-white shadow rounded">
        <h2 className="font-bold mb-2 border-b pb-1">2. Controller Decision</h2>
        <div className="text-xs overflow-y-auto max-h-48 space-y-1">
          {events.filter(e => e.event === 'controller_decision').reverse().map((e, i) => (
            <div key={i} className={'p-1 rounded ' + (e.decision === 'RETRIEVE' ? 'bg-green-100 text-green-800 font-bold' : 'bg-gray-100')}>
              {e.decision} - {e.reason}
            </div>
          ))}
        </div>
      </div>

      <div className="border p-4 bg-white shadow rounded">
        <h2 className="font-bold mb-2 border-b pb-1">3. Intents & Constraints</h2>
        <div className="space-y-2">
          {intents.map((intent, i) => (
            <div key={i} className="bg-blue-50 p-2 rounded text-xs">
              <strong>{intent.intent_id.split('-')[0]}</strong>: {intent.description}
              <div className="mt-1">
                {intent.constraints.map((c: any, j: number) => (
                  <span key={j} className="bg-blue-200 px-1 rounded mr-1">{c.key}={c.value}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border p-4 bg-white shadow rounded col-span-2">
        <h2 className="font-bold mb-2 border-b pb-1">4. Evidence Base (Preserved vs Updated)</h2>
        <div className="space-y-2 max-h-64 overflow-y-auto text-xs">
          {evidence.map((ev, i) => (
            <div key={i} className="bg-yellow-50 border border-yellow-200 p-2 rounded">
              <strong>[{ev.document_id} {ev.section_id}]</strong> - {ev.retrieval_source}
              <p className="mt-1 text-gray-700">{ev.text}</p>
              <div className="mt-1 text-gray-500">Intents: {ev.intent_ids.join(', ')}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="border p-4 bg-white shadow rounded">
        <h2 className="font-bold mb-2 border-b pb-1">5. Answer Versions</h2>
        <div className="space-y-4">
          {versions.map((v, i) => (
            <div key={i} className="border p-2 rounded bg-purple-50 text-xs">
              <h3 className="font-bold text-purple-800">Version {v.version}</h3>
              <p className="whitespace-pre-wrap mt-1">{v.rendered_answer}</p>
              <div className="mt-2 text-gray-600">
                <strong>Delta triggers:</strong> JSON.stringify(v.delta_summary)
              </div>
              <div className="mt-1 space-y-1">
                {v.claims?.map((c: any, j: number) => (
                  <div key={j} className="flex justify-between border-t pt-1 border-purple-200">
                    <span className="truncate w-3/4">{c.text}</span>
                    <span className={'font-bold ' + (c.status === 'SUPPORTED' ? 'text-green-600' : 'text-red-600')}>{c.status}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


