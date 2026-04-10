import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Database, 
  Cpu, 
  Layers, 
  Activity, 
  ChevronRight, 
  Info, 
  CheckCircle2, 
  AlertCircle,
  Clock,
  Zap,
  ToggleRight,
  BrainCircuit,
  ShieldCheck,
  Scale
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://localhost:8000';

const safeText = (val, def) => {
  if (!val) return def;
  if (typeof val === 'string') return val;
  if (Array.isArray(val)) return val.join(' ');
  if (typeof val === 'object') {
    try { return JSON.stringify(val); } catch(e) { return String(val); }
  }
  return String(val);
};

const App = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);
  
  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setDiagnosis(null);
    try {
      const resp = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: query })
      });
      if (!resp.ok) throw new Error('API server is not responding');
      const data = await resp.json();
      setResults(data);

      // Now run diagnosis pipeline
      const diagResp = await fetch(`${API_BASE}/diagnose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symptoms: [query] })
      });
      if (diagResp.ok) {
        const diagData = await diagResp.json();
        setDiagnosis(diagData);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafafa] text-slate-900 font-sans selection:bg-slate-200">
      {/* --- Top Navigation --- */}
      <nav className="border-b bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-white">
              <Activity size={18} />
            </div>
            <span className="font-semibold tracking-tight">Clinical Intelligence <span className="text-slate-400 font-normal">NLP</span></span>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'}`} />
              {error ? 'API Offline' : 'Systems Online'}
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-12">
        {/* --- Header Section --- */}
        <div className="text-center mb-16">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl font-bold tracking-tight mb-4"
          >
            Visual Semantic Discovery
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-slate-500 max-w-xl mx-auto text-lg leading-relaxed"
          >
            Visualize how our hybrid retrieval engine transforms natural language 
            into clinical insights using BM25 and Vector Search.
          </motion.p>
        </div>

        {/* --- Main Search --- */}
        <div className="max-w-2xl mx-auto mb-16">
          <form onSubmit={handleSearch} className="relative group">
            <input 
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter clinical symptoms or genomic markers..."
              className="w-full h-16 pl-14 pr-32 rounded-2xl border border-slate-200 bg-white shadow-sm focus:outline-none focus:ring-4 focus:ring-slate-100 transition-all text-lg placeholder:text-slate-400"
            />
            <div className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-slate-900 transition-colors">
              <Search size={22} />
            </div>
            <button 
              type="submit"
              disabled={loading}
              className="absolute right-3 top-1/2 -translate-y-1/2 h-10 px-6 rounded-xl bg-slate-900 text-white font-medium hover:bg-slate-800 transition-all disabled:bg-slate-200 disabled:text-slate-400 flex items-center gap-2"
            >
              {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Zap size={16} />}
              Analyze
            </button>
          </form>

          {error && (
            <div className="mt-4 p-4 rounded-xl bg-red-50 text-red-600 text-sm flex items-center gap-2 border border-red-100">
              <AlertCircle size={16} />
              {error}. Please run `python dashboard_api.py`.
            </div>
          )}
        </div>

        {results && (
          <div className="space-y-12">
            {/* --- Analysis Section --- */}
            <section>
              <div className="flex items-center gap-2 mb-6 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Cpu size={14} />
                NLP Processing Pipeline
              </div>
              <div className="p-6 rounded-2xl border bg-white shadow-sm">
                <div className="flex flex-wrap gap-3">
                  {results.tokens.slice(0, 15).map((token, i) => (
                    <motion.span 
                      key={i}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.05 }}
                      className="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-100 text-slate-700 font-medium text-sm flex items-center gap-1.5"
                    >
                      <CheckCircle2 size={12} className="text-green-500" />
                      {token}
                    </motion.span>
                  ))}
                  {results.tokens.length > 15 && (
                    <span className="text-slate-400 italic text-sm py-1.5 flex items-center">
                       ...and {results.tokens.length - 15} more context tokens
                    </span>
                  )}
                  {results.tokens.length === 0 && <span className="text-slate-400 italic">No significant keywords extracted.</span>}
                </div>
              </div>
            </section>



            {/* --- Final Ranked Results --- */}
            <section>
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                  <Database size={14} />
                  Retrieved Biomedical Context
                </div>
                <div className="flex items-center gap-4 text-xs font-medium text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Clock size={12} />
                    {results.stats.latency_ms}ms execution
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {results.fused_results.map((res, i) => (
                  <motion.div 
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="group p-8 rounded-3xl border bg-white shadow-sm hover:shadow-md hover:border-slate-300 transition-all relative overflow-hidden"
                  >
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-slate-900" />
                    <div className="flex flex-col gap-4">
                      <div>
                        <div className="flex items-center gap-3 mb-3">
                          <span className="text-xs font-medium text-slate-400 flex items-center gap-1">
                            <Info size={12} />
                            Source: {res.metadata?.source || 'Dataset'}
                          </span>
                          {res.metadata?.pmid && (
                             <span className="text-xs font-medium text-slate-400">
                               &middot; PMID: {res.metadata.pmid}
                             </span>
                          )}
                        </div>
                        <p className="text-slate-800 leading-relaxed font-normal italic">
                          "{res.text}"
                        </p>
                      </div>
                      
                      {res.metadata?.pmid && (
                         <div className="mt-2">
                            <a 
                              href={`https://pubmed.ncbi.nlm.nih.gov/${res.metadata.pmid}/`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-600 text-sm font-semibold hover:underline inline-flex items-center gap-1"
                            >
                              Read Full Article on PubMed <ChevronRight size={14} />
                            </a>
                         </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </section>

            {/* --- Clinical Inference UI --- */}
            {diagnosis && (
              <section className="mt-16 pt-8 border-t border-slate-200">
                 <div className="flex items-center gap-2 mb-8 text-sm font-semibold uppercase tracking-wider text-slate-900">
                    <BrainCircuit size={18} className="text-blue-500" />
                    Clinical Inference (LLM)
                 </div>
                 
                 <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Diagnosis */}
                    <div className="p-6 rounded-2xl bg-blue-50/50 border border-blue-100 flex flex-col h-full">
                       <h4 className="font-bold text-blue-900 mb-4 flex items-center gap-2">
                          <BrainCircuit size={16} /> Diagnoses
                       </h4>
                       <ul className="space-y-3 text-sm text-slate-700 flex-1">
                          {(() => {
                            const diagData = diagnosis?.diagnosis_stage;
                            if (!diagData) return null;
                            if (diagData.error) return <li className="text-red-500 font-medium">{safeText(diagData.error, "Unknown Error")}</li>;
                            
                            const diffs = diagData.differential_diagnoses;
                            if (!diffs) return null;
                            
                            if (Array.isArray(diffs)) {
                                return diffs.map((d, idx) => (
                                  <li key={idx} className="flex gap-2">
                                    <span className="font-semibold text-blue-700">{d?.condition || 'Unknown'}:</span>
                                    <span>{d?.confidence || ''}</span>
                                  </li>
                                ));
                            } else if (typeof diffs === 'object') {
                                return Object.entries(diffs).map(([condition, confidence], idx) => (
                                  <li key={idx} className="flex gap-2">
                                    <span className="font-semibold text-blue-700">{condition}:</span>
                                    <span>{String(confidence)}</span>
                                  </li>
                                ));
                            } else {
                                return <li>{String(diffs)}</li>;
                            }
                          })()}
                       </ul>
                    </div>

                    {/* Critic */}
                    <div className="p-6 rounded-2xl bg-amber-50/50 border border-amber-100 flex flex-col h-full">
                       <h4 className="font-bold text-amber-900 mb-4 flex items-center gap-2">
                          <Scale size={16} /> Reasoning Audit
                       </h4>
                       <p className="text-sm text-slate-700 leading-relaxed mb-4">
                          {safeText(diagnosis.critic_stage?.feedback_summary, "Evaluating reasoning...")}
                       </p>
                    </div>

                    {/* Safety */}
                    <div className="p-6 rounded-2xl bg-emerald-50/50 border border-emerald-100 flex flex-col h-full">
                       <h4 className="font-bold text-emerald-900 mb-4 flex items-center gap-2">
                          <ShieldCheck size={16} /> Safety Validated
                       </h4>
                       <p className="text-sm text-slate-700 leading-relaxed mb-4">
                           {safeText(diagnosis.safety_stage?.harm_assessment, "Checking for contraindications...")}
                       </p>
                       <div className="mt-auto flex items-center gap-2">
                           <span className={`px-2 py-1 text-xs font-bold rounded ${diagnosis.safety_stage?.approved ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                              {diagnosis.safety_stage?.approved ? 'APPROVED' : 'FLAGGED'}
                           </span>
                       </div>
                    </div>
                 </div>
              </section>
            )}
            
            {loading && !diagnosis && results && (
              <div className="mt-8 text-center text-sm text-slate-400 animate-pulse flex items-center justify-center gap-2">
                 <div className="w-4 h-4 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
                 Running Clinical Intelligence LLM Pipeline...
              </div>
            )}
          </div>
        )}

        {!results && !loading && (
          <div className="mt-24 text-center py-20 border-2 border-dashed border-slate-200 rounded-3xl bg-slate-50/50">
            <div className="w-16 h-16 rounded-full bg-white shadow-sm border border-slate-100 flex items-center justify-center mx-auto mb-6 text-slate-200">
              <Search size={32} />
            </div>
            <h3 className="text-slate-900 font-semibold mb-2">Ready for Discovery</h3>
            <p className="text-slate-500 text-sm max-w-sm mx-auto">
              Start by typing symptoms or medical conditions to see how the system understands and retrieves context.
            </p>
          </div>
        )}
      </main>
      
      <footer className="mt-24 pb-12 text-center text-xs text-slate-400">
        &copy; 2026 Antigravity Clinical Intelligence &middot; Built with shadcn/ui aesthetic
      </footer>
    </div>
  );
};

const MiniCard = ({ text, score, type }) => (
  <div className="p-4 rounded-xl border bg-white shadow-sm hover:border-slate-300 transition-colors flex items-center justify-between gap-4">
    <div className="flex-1 text-sm text-slate-600 line-clamp-1">
      {text}
    </div>
    <div className={`text-xs font-bold font-mono px-2 py-1 rounded ${type === 'bm25' ? 'bg-blue-50 text-blue-600' : 'bg-purple-50 text-purple-600'}`}>
      {score.toFixed(2)}
    </div>
  </div>
);

const EmptyState = ({ label }) => (
  <div className="p-4 rounded-xl border-2 border-dashed border-slate-100 text-xs text-slate-400 text-center uppercase tracking-widest">
    {label}
  </div>
);

export default App;
