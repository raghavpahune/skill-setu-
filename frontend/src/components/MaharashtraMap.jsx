import React from 'react';
import { Link } from 'react-router-dom';

const MAHA_DISTRICTS = [
  { name: 'Pune', jobs: 144, cluster: 'Western Maharashtra', focus: 'IT/ITES, Automotive, EV Hub' },
  { name: 'Mumbai', jobs: 125, cluster: 'Konkan', focus: 'Fintech, IT, Healthcare, SCM' },
  { name: 'Nagpur', jobs: 69, cluster: 'Vidarbha', focus: 'Logistics, Aerospace, Power, IoT' },
  { name: 'Thane', jobs: 64, cluster: 'Konkan', focus: 'Manufacturing, Chemicals, IT' },
  { name: 'Nashik', jobs: 44, cluster: 'North Maharashtra', focus: 'Auto Ancillaries, Pharma, CAD' },
  { name: 'Kolhapur', jobs: 31, cluster: 'Western Maharashtra', focus: 'Foundry, Precision Eng, Agri' },
  { name: 'Chhatrapati Sambhajinagar', jobs: 29, cluster: 'Marathwada', focus: 'Auto, Pharma, Welding, Solar' },
  { name: 'Amravati', jobs: 18, cluster: 'Vidarbha', focus: 'Textiles, AgriTech, Drones' },
  { name: 'Solapur', jobs: 16, cluster: 'Western Maharashtra', focus: 'Solar Energy, Textiles, Machining' },
  { name: 'Ratnagiri', jobs: 10, cluster: 'Konkan', focus: 'Marine, Processing, Tourism' },
];

export default function MaharashtraMap({ selectedDistrict, onSelectDistrict }) {
  return (
    <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white text-base">
            Maharashtra District Workforce Hubs
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Select any district to inspect local skill demand and district training plans</p>
        </div>
        <span className="text-xs bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold px-2.5 py-1 rounded-full border border-teal-200 dark:border-teal-800 self-start sm:self-auto">
          36 Districts Scalable Model
        </span>
      </div>

      {/* Interactive District Grid */}
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
                Focus: {d.focus}
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
    </div>
  );
}
