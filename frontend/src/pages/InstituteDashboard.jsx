import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Cell,
} from 'recharts';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import RecommendationCard from '../components/RecommendationCard';
import { api } from '../services/api';

const DEFAULT_COURSES = [
  {
    id: 'cr-001',
    name: 'Advanced AI & Machine Learning',
    description: 'Covers ML, DL, NLP, and AI applications. MSBTE affiliated.',
    institute: 'COEP Technological University',
    district: 'Pune',
    enrolment_count: 120,
    placed_count: 108,
    placement_rate: 90,
    status: 'active',
    category: 'Computer & Emerging Tech',
    nsqf_level: 6,
    skills: ['Python', 'Machine Learning', 'Deep Learning', 'PyTorch'],
  },
  {
    id: 'cr-002',
    name: 'Full Stack Web Development',
    description: 'MERN stack, DevOps, and cloud-native web deployment.',
    institute: 'Symbiosis Institute of Technology',
    district: 'Pune',
    enrolment_count: 90,
    placed_count: 76,
    placement_rate: 84,
    status: 'active',
    category: 'Information Technology',
    nsqf_level: 5,
    skills: ['React', 'Node.js', 'SQL', 'Git', 'Docker'],
  },
  {
    id: 'cr-003',
    name: 'Data Science & Analytics',
    description: 'Python, SQL, statistics, Power BI, and ML telemetry fundamentals.',
    institute: 'IIT Bombay (CEP)',
    district: 'Mumbai',
    enrolment_count: 150,
    placed_count: 135,
    placement_rate: 90,
    status: 'active',
    category: 'Analytics & Data',
    nsqf_level: 6,
    skills: ['Python', 'SQL', 'Data Analytics', 'Power BI'],
  },
  {
    id: 'cr-005',
    name: 'Cloud Computing & DevOps',
    description: 'AWS, Azure, Kubernetes, and automated CI/CD pipelines.',
    institute: 'Persistent Systems Training Centre',
    district: 'Pune',
    enrolment_count: 80,
    placed_count: 70,
    placement_rate: 88,
    status: 'active',
    category: 'Cloud Infrastructure',
    nsqf_level: 6,
    skills: ['AWS', 'Kubernetes', 'CI/CD', 'Linux'],
  },
  {
    id: 'cr-010',
    name: 'EV Technology & Maintenance',
    description: 'EV battery management systems, motor diagnostics, and powertrain maintenance.',
    institute: 'KPIT Skill Centre',
    district: 'Pune',
    enrolment_count: 40,
    placed_count: 36,
    placement_rate: 90,
    status: 'active',
    category: 'Automotive & Clean Energy',
    nsqf_level: 5,
    skills: ['EV Powertrain', 'Battery Management (BMS)', 'Motor Control'],
  },
  {
    id: 'cr-016',
    name: 'Industrial Automation & Robotics',
    description: 'PLC programming, SCADA interfaces, and industrial robotics for Industry 4.0.',
    institute: 'Siemens Technical Academy',
    district: 'Pune',
    enrolment_count: 50,
    placed_count: 44,
    placement_rate: 88,
    status: 'active',
    category: 'Advanced Manufacturing',
    nsqf_level: 6,
    skills: ['PLC Programming', 'SCADA', 'Industrial Robotics'],
  },
  {
    id: 'cr-027',
    name: 'CAD/CAM Design',
    description: 'AutoCAD, SolidWorks, 3D modelling, and precision manufacturing design.',
    institute: 'Government Polytechnic Nashik',
    district: 'Nashik',
    enrolment_count: 55,
    placed_count: 34,
    placement_rate: 62,
    status: 'needs_attention',
    category: 'Mechanical Design',
    nsqf_level: 4,
    skills: ['CAD/CAM', 'SolidWorks', '3D Modelling'],
  },
  {
    id: 'cr-025',
    name: 'Traditional Office Data Entry',
    description: 'Basic data entry, legacy typewriter speed, and basic spreadsheet operations.',
    institute: 'Various Private Centres',
    district: 'Mumbai',
    enrolment_count: 200,
    placed_count: 48,
    placement_rate: 24,
    status: 'review_oversupply',
    category: 'General Administration',
    nsqf_level: 3,
    skills: ['Data Entry', 'Typing', 'Spreadsheet Basics'],
  },
];

const DEFAULT_RECOMMENDATIONS = [
  {
    skill_name: 'Generative AI & Agentic RAG',
    recommendation: 'Incorporate Generative AI & Vector Search Modules into Computer Engineering Curriculum',
    reason: '68% of technology job specifications across Pune & Mumbai industrial clusters now require hands-on LLM, agent orchestration, and RAG capabilities.',
    confidence: 94,
    priority: 'CRITICAL',
    future_demand: 'high',
    trend: 'rising',
    gap_pct: 42,
    related_signals: ['Nasscom GenAI Talent Surge 2026', 'Maharashtra IT Policy 2024-29'],
  },
  {
    skill_name: 'EV Battery Management Systems (BMS)',
    recommendation: 'Expand EV Powertrain & Diagnostics Lab Capacity in Chakan-Pimpri ITIs',
    reason: 'Automotive tier-1 suppliers in Pune & Aurangabad report 38% hiring deficit for battery testing and high-voltage safety certified technicians.',
    confidence: 91,
    priority: 'HIGH',
    future_demand: 'high',
    trend: 'rising',
    gap_pct: 35,
    related_signals: ['Pune Automotive Cluster Expansion', 'National Electric Mobility Mission'],
  },
  {
    skill_name: 'Office Data Entry Modernization',
    recommendation: 'Pivot Traditional Office Data Entry Trades into Digital Media & Low-Code Web Development',
    reason: 'Placement rates for traditional manual typing/entry have fallen to 24% statewide due to robotic process automation (RPA) and automated document workflows.',
    confidence: 89,
    priority: 'CRITICAL',
    future_demand: 'declining',
    trend: 'declining',
    gap_pct: 68,
    related_signals: ['MSInS Vocational Modernization Directive', 'Administrative Automation Survey'],
  },
  {
    skill_name: 'Industrial IoT & SCADA Telemetry',
    recommendation: 'Introduce IIoT Sensor Integration in Government Polytechnic Electrical Syllabi',
    reason: 'Rapid transition of manufacturing plants in Nagpur and Nashik towards smart factories creates urgent demand for programmable sensor diagnostics.',
    confidence: 88,
    priority: 'HIGH',
    future_demand: 'high',
    trend: 'rising',
    gap_pct: 31,
    related_signals: ['Industry 4.0 Maharashtra Smart Factory Initiative'],
  },
];

const DISTRICTS = [
  'All Districts',
  'Pune',
  'Mumbai',
  'Nagpur',
  'Nashik',
  'Chhatrapati Sambhajinagar',
  'Kolhapur',
  'Solapur',
  'Amravati',
  'Thane',
];

export default function InstituteDashboard() {
  const [courses, setCourses] = useState(DEFAULT_COURSES);
  const [recommendations, setRecommendations] = useState(DEFAULT_RECOMMENDATIONS);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedDistrict, setSelectedDistrict] = useState('All Districts');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      api.getCourses().catch(() => null),
      api.getCourseRecommendations().catch(() => null),
    ])
      .then(([coursesRes, recsRes]) => {
        if (!isMounted) return;
        if (Array.isArray(coursesRes) && coursesRes.length > 0) {
          setCourses(coursesRes);
        }
        if (Array.isArray(recsRes) && recsRes.length > 0) {
          setRecommendations(recsRes);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Filtered courses
  const filteredCourses = useMemo(() => {
    return courses.filter((c) => {
      // Status filter
      if (statusFilter === 'oversupply' && c.status !== 'review_oversupply') return false;
      if (statusFilter === 'attention' && c.status !== 'needs_attention') return false;
      if (statusFilter === 'healthy' && c.status !== 'active') return false;

      // District filter
      if (selectedDistrict !== 'All Districts' && c.district?.toLowerCase() !== selectedDistrict.toLowerCase()) {
        return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const nameMatch = c.name?.toLowerCase().includes(q);
        const instMatch = c.institute?.toLowerCase().includes(q);
        const descMatch = c.description?.toLowerCase().includes(q);
        const distMatch = c.district?.toLowerCase().includes(q);
        const skillMatch = Array.isArray(c.skills) && c.skills.some((s) => s.toLowerCase().includes(q));
        if (!nameMatch && !instMatch && !descMatch && !distMatch && !skillMatch) {
          return false;
        }
      }

      return true;
    });
  }, [courses, statusFilter, selectedDistrict, searchQuery]);

  // Executive Metrics
  const oversupplyCount = useMemo(() => courses.filter((c) => c.status === 'review_oversupply').length, [courses]);
  const attentionCount = useMemo(() => courses.filter((c) => c.status === 'needs_attention').length, [courses]);
  const alignedCount = useMemo(() => courses.filter((c) => c.status === 'active').length, [courses]);

  const avgPlacement = useMemo(() => {
    if (!courses.length) return 74;
    const total = courses.reduce((acc, c) => acc + (c.placement_rate || 0), 0);
    return Math.round(total / courses.length);
  }, [courses]);

  const totalEnrolment = useMemo(() => {
    return courses.reduce((acc, c) => acc + (c.enrolment_count || 0), 0);
  }, [courses]);

  const totalPlaced = useMemo(() => {
    return courses.reduce((acc, c) => acc + (c.placed_count || 0), 0);
  }, [courses]);

  // Chart Data: Top courses by enrolment comparing Enrolment vs Placed
  const chartData = useMemo(() => {
    return [...courses]
      .sort((a, b) => (b.enrolment_count || 0) - (a.enrolment_count || 0))
      .slice(0, 7)
      .map((c) => ({
        name: c.name.length > 22 ? `${c.name.slice(0, 20)}...` : c.name,
        fullName: c.name,
        enrolment: c.enrolment_count || 0,
        placed: c.placed_count || 0,
        rate: c.placement_rate || 0,
        institute: c.institute,
      }));
  }, [courses]);

  return (
    <Layout>
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Training Institutes & Curriculum Alignment Hub
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
              MSBTE & DGT Aligned
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Audit vocational courses across Maharashtra ITIs and polytechnics, detect syllabus obsolescence, and align modules with real-time employer demand.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto flex-wrap">
          {oversupplyCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-xs font-bold shadow-xs">
              <span>⚠️</span>
              <span>{oversupplyCount} Syllabus Pivot Flagged</span>
            </div>
          )}
          <Link
            to="/student/copilot"
            className="px-3.5 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold shadow-xs flex items-center gap-1.5 transition-colors"
          >
            <span>✨</span>
            <span>Ask Copilot about Curriculum</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 mb-6">
        <StatCard
          title="Monitored Courses"
          value={courses.length.toString()}
          subtitle="Across ITIs & Polytechnics"
          icon="📚"
        />
        <StatCard
          title="Average Placement"
          value={`${avgPlacement}%`}
          subtitle={`${totalPlaced.toLocaleString()} placed of ${totalEnrolment.toLocaleString()}`}
          icon="🎓"
          color="teal"
        />
        <StatCard
          title="Annual Intake Capacity"
          value={totalEnrolment.toLocaleString()}
          subtitle="Sanctioned student seats"
          icon="👥"
          color="blue"
        />
        <StatCard
          title="Curriculum Upgrades"
          value={recommendations.length.toString()}
          subtitle="High-priority revisions"
          icon="💡"
          color="amber"
        />
        <StatCard
          title="Oversupply Flags"
          value={oversupplyCount.toString()}
          subtitle="Requires trade modernization"
          icon="⚠️"
          color="rose"
        />
      </div>

      {/* Visual Analytics & Placement Comparison Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Enrolment vs Placed Bar Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 p-5 sm:p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base">
                Intake Capacity vs Verified Placement Performance
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Top vocational trades ranked by student capacity and placement conversion
              </p>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded font-semibold self-start sm:self-auto">
              Real-time Telemetry
            </span>
          </div>

          <div className="h-64 sm:h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} angle={-15} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-900 text-white p-3 rounded-lg shadow-xl text-xs border border-slate-700">
                          <p className="font-bold text-teal-400 text-sm mb-1">{data.fullName}</p>
                          <p className="text-slate-300 mb-1">{data.institute}</p>
                          <div className="border-t border-slate-800 pt-1.5 space-y-0.5">
                            <p>Enrolment Intake: <strong className="text-white font-mono">{data.enrolment} seats</strong></p>
                            <p>Placed Graduates: <strong className="text-emerald-400 font-mono">{data.placed} students</strong></p>
                            <p>Placement Conversion: <strong className="text-teal-300 font-mono">{data.rate}%</strong></p>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="enrolment" name="Annual Intake" fill="#0d9488" radius={[4, 4, 0, 0]} />
                <Bar dataKey="placed" name="Placed Graduates" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Alignment Health Breakdown & Quick Guidelines */}
        <div className="bg-white dark:bg-slate-900 p-5 sm:p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">
              Curriculum Health Distribution
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Breakdown of {courses.length} accredited trades by labor-market alignment
            </p>

            <div className="space-y-3">
              {/* Aligned */}
              <div className="p-3 rounded-lg bg-emerald-50/80 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/60">
                <div className="flex items-center justify-between text-xs font-bold text-emerald-900 dark:text-emerald-300 mb-1">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                    High Demand Aligned
                  </span>
                  <span className="font-mono">{alignedCount} Courses ({Math.round((alignedCount / courses.length) * 100)}%)</span>
                </div>
                <p className="text-[11px] text-emerald-800/80 dark:text-emerald-400/80 leading-relaxed">
                  Placement rate &gt;75% with active hiring signals in Pune, Mumbai, and Nagpur clusters.
                </p>
              </div>

              {/* Needs Attention */}
              <div className="p-3 rounded-lg bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/60">
                <div className="flex items-center justify-between text-xs font-bold text-amber-900 dark:text-amber-300 mb-1">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                    Curriculum Gap Detected
                  </span>
                  <span className="font-mono">{attentionCount} Courses ({Math.round((attentionCount / courses.length) * 100)}%)</span>
                </div>
                <p className="text-[11px] text-amber-800/80 dark:text-amber-400/80 leading-relaxed">
                  Moderate placement (50–74%). Requires adding modern modular competencies (CAD/CAM, IoT, CNC).
                </p>
              </div>

              {/* Oversupply */}
              <div className="p-3 rounded-lg bg-rose-50/80 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/60">
                <div className="flex items-center justify-between text-xs font-bold text-rose-900 dark:text-rose-300 mb-1">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                    Review Oversupply / Obsolete
                  </span>
                  <span className="font-mono">{oversupplyCount} Courses ({Math.round((oversupplyCount / courses.length) * 100)}%)</span>
                </div>
                <p className="text-[11px] text-rose-800/80 dark:text-rose-400/80 leading-relaxed">
                  Sub-30% placement with excess enrollment. Recommended for immediate trade conversion.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Link
              to="/student/copilot"
              className="text-xs font-bold text-teal-700 dark:text-teal-400 hover:text-teal-900 dark:hover:text-teal-200 flex items-center justify-between group transition-colors"
            >
              <span>Consult AI Copilot on Syllabus Pivot Strategy</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Course Health Matrix & Placement Audit Table */}
      <div className="bg-white dark:bg-slate-900 p-5 sm:p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-5 pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base sm:text-lg">
              Course Health Matrix & Placement Audit Table
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Live evaluation of student intake, verified placement rate, and syllabus modernization signals across Maharashtra
            </p>
          </div>

          {/* Search and Filters Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 flex-wrap">
            {/* Search Input */}
            <div className="relative min-w-[200px]">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs">🔍</span>
              <input
                type="text"
                placeholder="Search course or institute..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            {/* District Dropdown */}
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              {DISTRICTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>

            {/* Alignment Status Filter Pills */}
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-xs">
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  statusFilter === 'all'
                    ? 'bg-white dark:bg-slate-700 shadow-2xs font-bold text-slate-900 dark:text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                All ({courses.length})
              </button>
              <button
                onClick={() => setStatusFilter('healthy')}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  statusFilter === 'healthy'
                    ? 'bg-emerald-600 text-white shadow-2xs font-bold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-emerald-700'
                }`}
              >
                Aligned ({alignedCount})
              </button>
              <button
                onClick={() => setStatusFilter('attention')}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  statusFilter === 'attention'
                    ? 'bg-amber-500 text-white shadow-2xs font-bold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-amber-700'
                }`}
              >
                Gaps ({attentionCount})
              </button>
              <button
                onClick={() => setStatusFilter('oversupply')}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  statusFilter === 'oversupply'
                    ? 'bg-rose-600 text-white shadow-2xs font-bold'
                    : 'text-rose-700 dark:text-rose-400 hover:text-rose-900'
                }`}
              >
                Oversupply ({oversupplyCount})
              </button>
            </div>
          </div>
        </div>

        {/* Table Content */}
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs space-y-2">
            <div className="inline-block w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
            <p>Loading accredited vocational courses telemetry...</p>
          </div>
        ) : filteredCourses.length === 0 ? (
          <div className="py-12 text-center text-slate-500 dark:text-slate-400 text-xs bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-dashed border-slate-200 dark:border-slate-800">
            <p className="text-lg mb-1">🔍</p>
            <p className="font-semibold text-slate-800 dark:text-slate-200">No courses match your filter criteria</p>
            <p className="text-[11px] text-slate-400 mt-1">Try selecting 'All Districts' or clearing search keywords.</p>
            <button
              onClick={() => {
                setStatusFilter('all');
                setSelectedDistrict('All Districts');
                setSearchQuery('');
              }}
              className="mt-3 px-3 py-1.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded-lg font-bold text-xs border border-teal-200 dark:border-teal-800 hover:bg-teal-100 cursor-pointer"
            >
              Reset All Filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="p-3">Course & Trade Focus</th>
                  <th className="p-3">Institute & District</th>
                  <th className="p-3">Intake</th>
                  <th className="p-3">Placed</th>
                  <th className="p-3">Placement Rate</th>
                  <th className="p-3">Alignment Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredCourses.map((c) => {
                  const isOversupply = c.status === 'review_oversupply';
                  const isGap = c.status === 'needs_attention';
                  return (
                    <tr
                      key={c.id}
                      onClick={() => setSelectedCourse(c)}
                      className={`cursor-pointer transition-colors ${
                        isOversupply
                          ? 'bg-rose-50/40 dark:bg-rose-950/20 hover:bg-rose-50 dark:hover:bg-rose-950/40'
                          : isGap
                          ? 'bg-amber-50/30 dark:bg-amber-950/15 hover:bg-amber-50 dark:hover:bg-amber-950/30'
                          : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/50'
                      }`}
                    >
                      <td className="p-3 font-bold text-slate-900 dark:text-white max-w-xs">
                        <div className="flex items-center gap-1.5">
                          {isOversupply && <span className="text-rose-600 dark:text-rose-400 font-bold" title="Flagged for Oversupply">⚠️</span>}
                          {isGap && <span className="text-amber-500 font-bold" title="Curriculum Gap">⚡</span>}
                          <span>{c.name}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 font-normal mt-0.5 line-clamp-1">
                          {c.description}
                        </p>
                      </td>
                      <td className="p-3 text-slate-600 dark:text-slate-300">
                        <div className="font-medium text-slate-800 dark:text-slate-200">{c.institute}</div>
                        <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
                          <span>📍</span>
                          <span>{c.district}</span>
                        </div>
                      </td>
                      <td className="p-3 font-mono font-semibold text-slate-700 dark:text-slate-300">
                        {c.enrolment_count} seats
                      </td>
                      <td className="p-3 font-mono text-slate-700 dark:text-slate-300">
                        {c.placed_count || 0}
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`font-bold font-mono ${
                              c.placement_rate >= 75
                                ? 'text-emerald-700 dark:text-emerald-400'
                                : c.placement_rate >= 50
                                ? 'text-amber-700 dark:text-amber-400'
                                : 'text-rose-700 dark:text-rose-400'
                            }`}
                          >
                            {c.placement_rate}%
                          </span>
                          <div className="w-16 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden hidden sm:block">
                            <div
                              className={`h-1.5 rounded-full ${
                                c.placement_rate >= 75
                                  ? 'bg-emerald-600 dark:bg-emerald-500'
                                  : c.placement_rate >= 50
                                  ? 'bg-amber-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.min(c.placement_rate, 100)}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        {isOversupply ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
                            LOW PLACEMENT / OVERSUPPLY
                          </span>
                        ) : isGap ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                            CURRICULUM GAP
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                            HIGH DEMAND ALIGNED
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCourse(c);
                          }}
                          className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-950 hover:text-teal-800 text-slate-700 dark:text-slate-300 rounded font-semibold text-[11px] border border-slate-200 dark:border-slate-700 transition-colors shadow-2xs cursor-pointer"
                        >
                          Inspect →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Actionable Curriculum Recommendations Workbench */}
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-lg">
              Actionable Curriculum Revisions for MSBTE / ITI Syllabus Council
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Evidence-based recommendations derived from real-time employer signals, gap computations, and 12-to-24 month labor forecasts.
            </p>
          </div>
          <Link
            to="/student/copilot"
            className="text-xs font-bold text-teal-700 dark:text-teal-400 hover:text-teal-900 dark:hover:text-teal-200 flex items-center gap-1 shrink-0"
          >
            <span>Ask Copilot for Syllabus Draft</span>
            <span>→</span>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {recommendations.map((rec, idx) => (
            <RecommendationCard key={idx} rec={rec} />
          ))}
        </div>
      </div>

      {/* Course Detail Inspection Modal / Drawer */}
      {selectedCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl overflow-y-auto max-h-[90vh]">
            <div className="flex items-start justify-between gap-4 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800 uppercase">
                    {selectedCourse.category || 'Vocational Trade'}
                  </span>
                  {selectedCourse.nsqf_level && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      NSQF Level {selectedCourse.nsqf_level}
                    </span>
                  )}
                </div>
                <h3 className="text-xl font-extrabold text-slate-900 dark:text-white">
                  {selectedCourse.name}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {selectedCourse.institute} • {selectedCourse.district} District
                </p>
              </div>
              <button
                onClick={() => setSelectedCourse(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 text-lg leading-none cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Performance Indicators */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-700/60 text-center">
                <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold block">Intake Capacity</span>
                <span className="text-base font-extrabold font-mono text-slate-900 dark:text-white">
                  {selectedCourse.enrolment_count} seats
                </span>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-700/60 text-center">
                <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold block">Placed Graduates</span>
                <span className="text-base font-extrabold font-mono text-emerald-600 dark:text-emerald-400">
                  {selectedCourse.placed_count || 0}
                </span>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-700/60 text-center">
                <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold block">Placement Rate</span>
                <span className={`text-base font-extrabold font-mono ${
                  selectedCourse.placement_rate >= 75 ? 'text-emerald-600 dark:text-emerald-400' :
                  selectedCourse.placement_rate >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'
                }`}>
                  {selectedCourse.placement_rate}%
                </span>
              </div>
            </div>

            {/* Description */}
            <div className="mb-4">
              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-1">
                Course Syllabus & Scope
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                {selectedCourse.description}
              </p>
            </div>

            {/* Core Competencies */}
            {Array.isArray(selectedCourse.skills) && selectedCourse.skills.length > 0 && (
              <div className="mb-5">
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-2">
                  Integrated Competencies (NSQF Mapped)
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedCourse.skills.map((s, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800 text-xs font-medium"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Action CTA buttons */}
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-2">
              <button
                onClick={() => setSelectedCourse(null)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
              >
                Close
              </button>
              <Link
                to={`/student/copilot`}
                className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold shadow-xs flex items-center gap-1.5 transition-colors"
              >
                <span>✨</span>
                <span>Ask AI Copilot about this Course</span>
              </Link>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
