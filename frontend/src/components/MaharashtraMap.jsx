import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const MAHA_DISTRICTS = [
  { name: 'Pune', jobs: 144, cluster: 'Western Maharashtra', focus: 'IT/ITES, Automotive, EV Hub', x: 32, y: 58, color: '#0d9488' },
  { name: 'Mumbai', jobs: 125, cluster: 'Konkan', focus: 'Fintech, IT, Healthcare, SCM', x: 18, y: 46, color: '#3b82f6' },
  { name: 'Thane', jobs: 64, cluster: 'Konkan', focus: 'Manufacturing, Chemicals, IT', x: 22, y: 42, color: '#3b82f6' },
  { name: 'Nagpur', jobs: 69, cluster: 'Vidarbha', focus: 'Logistics, Aerospace, Power, IoT', x: 82, y: 24, color: '#8b5cf6' },
  { name: 'Nashik', jobs: 44, cluster: 'North Maharashtra', focus: 'Auto Ancillaries, Pharma, CAD', x: 30, y: 34, color: '#f59e0b' },
  { name: 'Kolhapur', jobs: 31, cluster: 'Western Maharashtra', focus: 'Foundry, Precision Eng, Agri', x: 34, y: 82, color: '#0d9488' },
  { name: 'Chhatrapati Sambhajinagar', jobs: 29, cluster: 'Marathwada', focus: 'Auto, Pharma, Welding, Solar', x: 46, y: 44, color: '#ec4899' },
  { name: 'Amravati', jobs: 18, cluster: 'Vidarbha', focus: 'Textiles, AgriTech, Drones', x: 68, y: 28, color: '#8b5cf6' },
  { name: 'Solapur', jobs: 16, cluster: 'Western Maharashtra', focus: 'Solar Energy, Textiles, Machining', x: 48, y: 70, color: '#0d9488' },
  { name: 'Ratnagiri', jobs: 10, cluster: 'Konkan', focus: 'Marine, Processing, Tourism', x: 24, y: 72, color: '#3b82f6' },
];

export default function MaharashtraMap({ selectedDistrict = 'Pune', onSelectDistrict }) {
  const [viewMode, setViewMode] = useState('both'); // 'both' | 'map' | 'grid'
  const active = MAHA_DISTRICTS.find(
    (d) => d.name.toLowerCase() === selectedDistrict?.toLowerCase()
  ) || MAHA_DISTRICTS[0];

  return (
    <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs transition-colors">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Maharashtra District Workforce Intelligence Map
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
              Interactive Hub
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Click on any district node or card to inspect real-time labour demand, sector focus, and capacity gaps
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg text-xs border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setViewMode('both')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                viewMode === 'both' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-bold shadow-2xs' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                viewMode === 'grid' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-bold shadow-2xs' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
              }`}
            >
              Grid
            </button>
          </div>

          <Link
            to={`/government/district/${encodeURIComponent(active.name)}`}
            className="px-3 py-1.5 bg-slate-900 dark:bg-teal-600 hover:bg-slate-800 dark:hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors whitespace-nowrap"
          >
            Open {active.name} Plan →
          </Link>
        </div>
      </div>

      {/* Main Container: Map Visual + Selected Panel */}
      {(viewMode === 'both' || viewMode === 'map') && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
          {/* Interactive Geo Canvas */}
          <div className="lg:col-span-2 relative bg-slate-900 rounded-xl p-4 min-h-[300px] sm:min-h-[340px] flex flex-col justify-between border border-slate-800 overflow-hidden">
            {/* Background Map Grid Effect */}
            <div className="absolute inset-0 bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:16px_16px] opacity-40"></div>
            
            {/* State Outline Watermark */}
            <div className="absolute top-4 left-4 z-10">
              <span className="text-[11px] font-mono uppercase tracking-wider text-teal-400 font-semibold bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                State Geo-Cluster Canvas
              </span>
            </div>

            {/* District Pins Container */}
            <div className="relative w-full h-[260px] sm:h-[300px] my-auto">
              {MAHA_DISTRICTS.map((d) => {
                const isSelected = selectedDistrict?.toLowerCase() === d.name.toLowerCase();
                return (
                  <button
                    key={d.name}
                    onClick={() => onSelectDistrict && onSelectDistrict(d.name)}
                    style={{ left: `${d.x}%`, top: `${d.y}%` }}
                    className={`absolute -translate-x-1/2 -translate-y-1/2 group transition-all duration-300 focus:outline-none z-20`}
                  >
                    <div className="flex flex-col items-center">
                      <span className={`w-3.5 h-3.5 rounded-full border-2 transition-transform duration-200 ${
                        isSelected
                          ? 'bg-teal-400 border-white scale-150 shadow-[0_0_12px_#2dd4bf]'
                          : 'bg-slate-700 border-slate-400 group-hover:scale-125 group-hover:bg-teal-400'
                      }`} />
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded mt-1 whitespace-nowrap transition-all shadow-md ${
                        isSelected
                          ? 'bg-teal-500 text-slate-950 font-extrabold'
                          : 'bg-slate-800/90 text-slate-200 border border-slate-700 group-hover:bg-slate-700'
                      }`}>
                        {d.name} ({d.jobs})
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Map Cluster Legend */}
            <div className="relative z-10 flex flex-wrap items-center gap-3 pt-2 border-t border-slate-800 text-[10px] text-slate-400">
              <span className="font-semibold text-slate-300">Cluster Zones:</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-teal-500"></span> Western Maha</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Konkan</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500"></span> Vidarbha</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"></span> North Maha</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-pink-500"></span> Marathwada</span>
            </div>
          </div>

          {/* Selected District Quick Snapshot */}
          <div className="bg-slate-50 dark:bg-slate-800/60 p-5 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
                  {active.cluster}
                </span>
                <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300">
                  {active.jobs} Active Jobs
                </span>
              </div>

              <h4 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight mb-1">
                {active.name} District
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                Primary Industrial Sector Focus
              </p>

              <div className="p-3 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 mb-4 text-xs">
                <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Target Hiring Specializations:
                </span>
                <p className="text-teal-800 dark:text-teal-300 font-medium">
                  {active.focus}
                </p>
              </div>

              <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                <div className="flex justify-between py-1 border-b border-slate-200/60 dark:border-slate-700/60">
                  <span>Workforce Demand Share:</span>
                  <span className="font-bold text-slate-900 dark:text-white">{Math.round((active.jobs / 550) * 100)}% of State</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-200/60 dark:border-slate-700/60">
                  <span>Training Seat Deficit:</span>
                  <span className="font-bold text-rose-600 dark:text-rose-400">High Deficit (32%)</span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 border-t border-slate-200 dark:border-slate-700">
              <Link
                to={`/government/district/${encodeURIComponent(active.name)}`}
                className="w-full py-2 bg-slate-900 dark:bg-teal-600 hover:bg-slate-800 dark:hover:bg-teal-700 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-xs"
              >
                <span>Inspect Detailed {active.name} Training Plan</span>
                <span>→</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Interactive District Grid */}
      {(viewMode === 'both' || viewMode === 'grid') && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {MAHA_DISTRICTS.map((d) => {
            const isSelected = selectedDistrict?.toLowerCase() === d.name.toLowerCase();
            return (
              <div
                key={d.name}
                onClick={() => onSelectDistrict && onSelectDistrict(d.name)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer text-left ${
                  isSelected
                    ? 'bg-slate-900 dark:bg-teal-950 text-white border-slate-900 dark:border-teal-700 shadow-md ring-2 ring-teal-500/50 scale-[1.02]'
                    : 'bg-slate-50 dark:bg-slate-800/60 hover:bg-white dark:hover:bg-slate-800 text-slate-900 dark:text-white border-slate-200 dark:border-slate-700/80 hover:border-teal-400 dark:hover:border-teal-600 hover:shadow-xs'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm">{d.name}</span>
                  <span className={`text-xs font-mono font-semibold px-1.5 py-0.5 rounded ${
                    isSelected
                      ? 'bg-teal-500 text-slate-950 font-bold'
                      : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                  }`}>
                    {d.jobs} jobs
                  </span>
                </div>
                <p className={`text-[11px] mt-1 line-clamp-1 ${isSelected ? 'text-slate-300' : 'text-slate-500 dark:text-slate-400'}`}>
                  {d.cluster}
                </p>
                <p className={`text-[11px] mt-1.5 font-medium line-clamp-1 ${isSelected ? 'text-teal-300' : 'text-teal-700 dark:text-teal-400'}`}>
                  {d.focus}
                </p>

                <div className="mt-2.5 pt-2 border-t border-slate-200/50 dark:border-slate-700/50 flex justify-between items-center text-[10px]">
                  <Link
                    to={`/government/district/${encodeURIComponent(d.name)}`}
                    className={`font-semibold hover:underline flex items-center gap-0.5 ${
                      isSelected ? 'text-teal-300' : 'text-slate-900 dark:text-slate-300'
                    }`}
                    onClick={(e) => e.stopPropagation()}
                  >
                    View Plan →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
