import { useState, useEffect, useRef } from 'react';

type WsStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED';
type Message = { id: string; role: 'user' | 'bot'; content: string };

function App() {
  const [sessionId, setSessionId] = useState(() => 'sess_' + Date.now());
  const [wsStatus, setWsStatus] = useState<WsStatus>('DISCONNECTED');
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const transcriptRef = useRef(''); // Ref to fix stale closure in socket.onmessage
  
  const [intents, setIntents] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [controllerDecision, setControllerDecision] = useState<any>(null);
  const [timeline, setTimeline] = useState<{ts: string, msg: string, detail?: string}[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const [userInput, setUserInput] = useState('');
  const [globalSeq, setGlobalSeq] = useState(0);
  const [isListening, setIsListening] = useState(false);
  const manualStopRef = useRef(false);
  const recognitionRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentTranscript]);

  const speak = (text: string) => {
    if (!window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  };

  const connectWebSocket = (currentSessionId: string) => {
    setWsStatus('CONNECTING');
    const socket = new WebSocket(`ws://localhost:8000/ws/${currentSessionId}`);

    socket.onopen = () => {
      setWsStatus('CONNECTED');
    };

    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      const ts = new Date().toISOString().split('T')[1].slice(0, 12);
      
      if (data.event === 'controller_decision') {
        setControllerDecision(data);
        setCurrentTranscript(data.text || '');
        transcriptRef.current = data.text || ''; // Sync to ref
        if (data.decision !== 'WAIT') {
          setTimeline(prev => [...prev, {ts, msg: 'CONTROLLER_' + data.decision, detail: data.reason}]);
        }
      }
      
      if (data.event === 'intents_extracted') {
        setIntents(data.intents);
        setTimeline(prev => [...prev, {ts, msg: 'INTENTS_EXTRACTED', detail: `${data.intents.length} intents`}]);
      }
      
      if (data.event === 'answer_generated') {
        if (data.evidence) {
            setEvidence(data.evidence);
            setTimeline(prev => [...prev, {ts, msg: 'EVIDENCE_RETRIEVED', detail: `${data.evidence.length} chunks`}]);
        }
        
        const ans = data.answer; // This is the AnswerVersion object
        setTimeline(prev => [...prev, {ts, msg: 'ANSWER_V' + ans.version, detail: `Claims: ${ans.claims.length}`}]);
        
        setMessages(prev => {
           let newMessages = [...prev];
           if (newMessages.length === 0 || newMessages[newMessages.length - 1].role !== 'user') {
               const turns = transcriptRef.current.split('\n\n'); // Read from ref to avoid closure capture
               newMessages.push({ id: `usr-${Date.now()}`, role: 'user', content: turns[turns.length - 1] });
           }
           newMessages.push({ id: `bot-v${ans.version}-${Date.now()}`, role: 'bot', content: ans.rendered_answer });
           return newMessages;
        });
        
        speak(ans.rendered_answer);
      }
    };

    socket.onclose = () => {
      setWsStatus('DISCONNECTED');
      setTimeout(() => connectWebSocket(currentSessionId), 3000);
    };

    socket.onerror = (err) => {
      console.error('WebSocket Error:', err);
    };
    
    wsRef.current = socket;
    return socket;
  };

  useEffect(() => {
    connectWebSocket(sessionId);
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [sessionId]);

  const ensureConnection = async (): Promise<WebSocket> => {
    let currentWs = wsRef.current;
    if (!currentWs || currentWs.readyState === WebSocket.CLOSED || currentWs.readyState === WebSocket.CLOSING) {
      currentWs = connectWebSocket(sessionId);
    }
    
    if (currentWs.readyState === WebSocket.CONNECTING) {
      await new Promise(resolve => {
        const check = setInterval(() => {
          if (currentWs?.readyState === WebSocket.OPEN) {
            clearInterval(check); resolve(true);
          } else if (currentWs?.readyState === WebSocket.CLOSED) {
            clearInterval(check); resolve(false);
          }
        }, 100);
      });
    }
    return currentWs;
  };

  const toggleVoice = async () => {
    if (isListening) {
      manualStopRef.current = true;
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    try {
      const activeWs = await ensureConnection();
      if (activeWs.readyState !== WebSocket.OPEN) return;

      const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Voice recognition is not supported in this browser. Please use Chrome.");
        return;
      }

      if (timeline.length === 0) {
          setTimeline([{ts: new Date().toISOString().split('T')[1].slice(0, 12), msg: 'SYSTEM_READY', detail: 'Running Voice mode'}]);
      } else {
          setTimeline(prev => [...prev, {ts: new Date().toISOString().split('T')[1].slice(0, 12), msg: 'SYSTEM_READY', detail: 'Started Voice mode'}]);
      }
      
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      
      let lastWordsLength = 0;
      let currentSeq = globalSeq;
      const runId = Date.now();

      recognition.onstart = () => setIsListening(true);
      
      recognition.onend = () => {
         setIsListening(false);
         activeWs.send(JSON.stringify({
             type: 'chunk', chunk_id: `voice_${runId}_final`, seq: currentSeq, t_ms: currentSeq * 200, text: '', is_final: true
         }));
         setGlobalSeq(currentSeq + 1);
      };
      
      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        
        const currentWords = transcript.trim().split(/\s+/);
        if (currentWords.length > lastWordsLength) {
            const newWords = currentWords.slice(lastWordsLength);
            for (let w of newWords) {
                if (w.trim()) {
                    activeWs.send(JSON.stringify({
                        type: 'chunk', chunk_id: `voice_${runId}_${currentSeq}`, seq: currentSeq, t_ms: currentSeq * 200, text: w.trim(), is_final: false
                    }));
                    currentSeq++;
                }
            }
            lastWordsLength = currentWords.length;
        }
      };
      
      recognitionRef.current = recognition;
      recognition.start();

    } catch (e) {
      console.error(e);
      setIsListening(false);
    }
  };

  const handleInteractiveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim()) return;
    
    const textToStream = userInput.trim();
    setUserInput(''); 
    
    try {
      const activeWs = await ensureConnection();
      if (activeWs.readyState !== WebSocket.OPEN) return;
      
      if (timeline.length === 0) {
          setTimeline([{ts: new Date().toISOString().split('T')[1].slice(0, 12), msg: 'SYSTEM_READY', detail: 'Running interactive session'}]);
      }
      
      const words = textToStream.split(" ");
      let currentSeq = globalSeq;
      
      for (let i = 0; i < words.length; i++) {
        let word = words[i];
        if (i === 0 && currentTranscript.length > 0) {
            word = "\n\n" + word;
        }
        
        if (activeWs.readyState === WebSocket.OPEN) {
          activeWs.send(JSON.stringify({ 
              type: 'chunk', chunk_id: 'interactive_' + Date.now() + '_' + currentSeq, seq: currentSeq, t_ms: currentSeq * 200, text: word, is_final: i === words.length - 1 
          }));
        }
        currentSeq++;
        await new Promise(r => setTimeout(r, 200));
      }
      setGlobalSeq(currentSeq);
    } catch (err) {
      console.error(err);
    }
  };

  const clearSession = async () => {
      if (wsRef.current) wsRef.current.close(); // Force disconnect old session
      setMessages([]); setIntents([]); setEvidence([]); setCurrentTranscript(''); setControllerDecision(null);
      transcriptRef.current = '';
      setTimeline([{ts: new Date().toISOString().split('T')[1].slice(0, 12), msg: 'SYSTEM_READY', detail: 'Session Cleared'}]);
      setGlobalSeq(0);
      setSessionId('sess_' + Date.now()); // Triggers useEffect to reconnect with fresh state
  };

  return (
    <div className="h-screen bg-slate-950 text-slate-300 font-sans flex flex-col overflow-hidden">
      
      <header className="border-b border-slate-800 p-4 flex justify-between items-center bg-slate-900 shadow-lg shrink-0">
        <div>
          <h1 className="text-xl font-bold text-emerald-500 tracking-wider">LIVE CHAT RAG</h1>
          <div className="text-slate-500 text-xs mt-1 flex items-center gap-3">
            Samsung PRISM Theme 4
            <span className={`px-2 py-0.5 rounded font-bold ${wsStatus === 'CONNECTED' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-rose-900/50 text-rose-400'}`}>
              WS: {wsStatus}
            </span>
          </div>
        </div>
        <button 
          onClick={clearSession}
          className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded text-sm font-bold transition-colors border border-slate-700"
        >
          Clear Memory
        </button>
      </header>

      <div className="flex-1 overflow-hidden flex">
        
        {/* LEFT PANEL: CHAT INTERFACE */}
        <div className="flex-1 flex flex-col border-r border-slate-800 bg-slate-950 relative">
           
           <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-32">
              {messages.length === 0 && !currentTranscript && (
                  <div className="text-center text-slate-600 mt-20">
                      <div className="text-4xl mb-4">👋</div>
                      Type a message or use the microphone below to start a live streaming conversation.
                  </div>
              )}
              
              {messages.map(msg => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[75%] rounded-2xl p-4 shadow-lg whitespace-pre-wrap ${msg.role === 'user' ? 'bg-emerald-600 text-white rounded-tr-sm' : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm'}`}>
                          {msg.content}
                      </div>
                  </div>
              ))}
              
              {/* STREAMING USER BUBBLE */}
              {currentTranscript && (messages.length === 0 || messages[messages.length-1].role === 'bot') && (
                  <div className="flex justify-end">
                      <div className="max-w-[75%] rounded-2xl rounded-tr-sm p-4 bg-emerald-900/40 text-emerald-100 border border-emerald-700/50">
                          <div className="flex items-center gap-2 mb-2">
                             <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                             <div className="text-[10px] font-bold opacity-70 uppercase tracking-widest">Streaming...</div>
                          </div>
                          {currentTranscript.split('\n\n').pop()}
                      </div>
                  </div>
              )}
              
              <div ref={messagesEndRef} />
           </div>

           {/* CHAT INPUT AREA */}
           <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-slate-950 via-slate-950 to-transparent p-6 pt-12">
             <form onSubmit={handleInteractiveSubmit} className="flex gap-3 max-w-4xl mx-auto relative">
               <button
                 type="button"
                 onClick={toggleVoice}
                 disabled={wsStatus !== 'CONNECTED'}
                 className={"p-4 rounded-xl font-bold transition-all text-xl flex items-center justify-center shrink-0 " + (isListening ? 'bg-rose-600 text-white shadow-[0_0_20px_rgba(225,29,72,0.6)] animate-pulse' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white')}
                 title={isListening ? "Stop listening" : "Start Voice Streaming"}
               >
                 🎤
               </button>
               <input 
                 type="text" 
                 value={userInput}
                 onChange={(e) => setUserInput(e.target.value)}
                 placeholder={isListening ? "Listening... Speak now!" : "Message the streaming agent..."}
                 disabled={isListening}
                 className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-5 py-4 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all disabled:opacity-50 shadow-inner"
               />
               <button 
                 type="submit" 
                 disabled={!userInput.trim() || wsStatus !== 'CONNECTED' || isListening}
                 className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-4 rounded-xl font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
               >
                 Send
               </button>
             </form>
           </div>
        </div>

        {/* RIGHT PANEL: UNDER THE HOOD DASHBOARD */}
        <div className="w-full lg:w-[400px] flex flex-col bg-slate-900 shrink-0">
            <div className="p-4 border-b border-slate-800 bg-slate-950/50 shrink-0 flex items-center gap-2">
               <span className="text-amber-500">⚙️</span>
               <h2 className="text-slate-300 font-bold text-xs tracking-widest uppercase">Internal RAG State</h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
                
                {/* CONTROLLER */}
                <div>
                    <h3 className="text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Controller Decision</h3>
                    <div className="flex items-center gap-3">
                        <div className={"px-3 py-1 rounded-sm font-bold text-xs " + (controllerDecision?.decision === 'WAIT' ? 'bg-amber-900/50 text-amber-500 border border-amber-800/50' : 'bg-emerald-900/50 text-emerald-500 border border-emerald-800/50')}>
                          {controllerDecision?.decision || 'IDLE'}
                        </div>
                        <div className="text-xs text-slate-400 font-mono">
                          {controllerDecision?.reason || 'waiting for input...'}
                        </div>
                    </div>
                </div>
                
                {/* INTENTS */}
                <div>
                    <h3 className="text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Multi-Intent Extractor</h3>
                    {intents.length === 0 ? <div className="text-slate-600 text-xs italic">No intents detected</div> : (
                        <div className="space-y-2">
                            {intents.map(int => (
                                <div key={int.intent_id} className="text-xs bg-slate-800/50 p-3 border-l-2 border-emerald-500 rounded-r">
                                    <div className="text-slate-200">{int.description}</div>
                                    <div className="flex justify-between items-center mt-2">
                                      <span className={"text-[10px] px-1.5 py-0.5 rounded " + (int.status === 'PRESERVED' ? 'bg-blue-900/50 text-blue-300' : 'bg-slate-700 text-slate-400')}>
                                        {int.status || 'NEW'}
                                      </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                
                {/* EVIDENCE */}
                <div>
                    <h3 className="text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Evidence Base</h3>
                    {evidence.length === 0 ? <div className="text-slate-600 text-xs italic">No corpus evidence loaded</div> : (
                        <div className="space-y-2">
                            {evidence.map((c, i) => (
                                <div key={i} className="text-[11px] bg-slate-800/30 p-2.5 rounded border border-slate-700/50 text-slate-400 leading-relaxed">
                                    {c.text.substring(0, 150)}...
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* TELEMETRY */}
                <div className="pt-4 border-t border-slate-800/50">
                  <h3 className="text-[10px] font-bold text-slate-500 mb-3 tracking-widest uppercase">Event Telemetry</h3>
                  <div className="space-y-2 text-[10px] font-mono">
                    {timeline.slice(-10).map((t, i) => (
                      <div key={i} className="flex gap-3 text-slate-400">
                        <span className="text-slate-600 shrink-0">{t.ts}</span>
                        <div>
                          <div className={t.msg.includes('SYSTEM') ? 'text-blue-400' : 'text-emerald-500'}>{t.msg}</div>
                          {t.detail && <div className="text-slate-500">{t.detail}</div>}
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

export default App;
