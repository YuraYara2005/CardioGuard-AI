import { useState, useEffect } from 'react';

import { useAuth } from '../store/AuthContext';
import { generateClinicalReports } from '../api/reportService';

import type { ClinicalReport } from '../types';

import {
  Heart,
  ShieldCheck,
  AlertCircle,
  LogOut,
  Activity,
  Loader2,
  ClipboardList,
  ChevronLeft,
} from 'lucide-react';


// ============================================================
// Helper: map urgency to Arabic label
// ============================================================

function urgencyAr(
  level?: string,
): {
  label: string;
  colorClass: string;
} {
  switch (level) {
    case 'CRITICAL':
      return {
        label: 'حرج – مراجعة فورية',
        colorClass:
          'text-red-400 bg-red-500/10 border-red-500/30',
      };

    case 'HIGH':
      return {
        label: 'مرتفع – مراجعة قريبة',
        colorClass:
          'text-orange-400 bg-orange-500/10 border-orange-500/30',
      };

    case 'MEDIUM':
      return {
        label: 'متوسط – متابعة دورية',
        colorClass:
          'text-amber-400 bg-amber-500/10 border-amber-500/30',
      };

    default:
      return {
        label: 'منخفض – وضع مستقر',
        colorClass:
          'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
      };
  }
}


// ============================================================
// Helper: convert backend patient report string
// into the ClinicalReport shape used by this UI
// ============================================================

function buildPatientClinicalReport(
  patientReport: string,
  isEmergency: boolean,
): ClinicalReport {
  return {
    language: 'ar',

    title: isEmergency
      ? 'تقرير متابعة القلب'
      : 'نتيجة المتابعة القلبية',

    summary: patientReport,

    guidelines: [],

    recommendations: [],

    urgency_level: isEmergency
      ? 'CRITICAL'
      : 'LOW',

    generated_at: new Date().toISOString(),
  };
}


// ============================================================
// Info Card
// ============================================================

function InfoCard({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`
        rounded-2xl
        border border-white/5
        bg-white/[0.04]
        backdrop-blur-xl
        shadow-lg
        p-6
        ${className}
      `}
    >
      {children}
    </div>
  );
}


// ============================================================
// Patient Portal
// ============================================================

export default function PatientPortal() {
  const { user, logout } = useAuth();

  const [report, setReport] =
    useState<ClinicalReport | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');


  // ==========================================================
  // Load Patient Report
  // ==========================================================

  useEffect(() => {
    async function loadReport() {
      try {
        setLoading(true);
        setError('');

        const isEmergency = false;

        const result = await generateClinicalReports({
          diagnosis:
            'Normal ECG — routine monitoring',

          confidence_score: 0.92,

          is_emergency: isEmergency,
        });


        // Backend currently returns patient_report as string.
        // Convert it into the ClinicalReport object expected
        // by the existing Patient Portal UI.
        const clinicalReport =
          buildPatientClinicalReport(
            result.patient_report,
            isEmergency,
          );

        setReport(clinicalReport);

      } catch (err) {
        console.error(
          '[PatientPortal] Failed to load report:',
          err,
        );

        setError(
          'تعذّر تحميل التقرير. يرجى المحاولة لاحقًا.',
        );

      } finally {
        setLoading(false);
      }
    }

    void loadReport();
  }, []);


  const urgency = urgencyAr(
    report?.urgency_level,
  );


  // ==========================================================
  // Render
  // ==========================================================

  return (
    <div
      dir="rtl"
      lang="ar"
      className="
        min-h-screen
        bg-cg-bg
        flex flex-col
      "
      style={{
        fontFamily:
          "'Segoe UI', 'Arial', sans-serif",
      }}
    >

      {/* ====================================================
          Decorative Background
      ==================================================== */}

      <div className="fixed inset-0 overflow-hidden pointer-events-none">

        <div
          className="
            absolute
            -top-32 -right-32
            w-80 h-80
            bg-indigo-600/8
            rounded-full
            blur-3xl
          "
        />

        <div
          className="
            absolute
            -bottom-32 -left-32
            w-80 h-80
            bg-emerald-500/8
            rounded-full
            blur-3xl
          "
        />

      </div>


      {/* ====================================================
          Top Bar
      ==================================================== */}

      <header
        className="
          relative
          border-b border-cg-border
          bg-cg-surface/60
          backdrop-blur-md
          px-6 py-4
        "
      >
        <div
          className="
            max-w-2xl mx-auto
            flex items-center justify-between
          "
        >

          {/* Brand */}
          <div className="flex items-center gap-3">

            <div
              className="
                w-9 h-9
                rounded-xl
                bg-indigo-600/20
                border border-indigo-500/30
                flex items-center justify-center
              "
            >
              <Activity className="w-5 h-5 text-indigo-400" />
            </div>

            <div>
              <span className="block text-sm font-bold text-white leading-tight">
                كاردیوغارد AI
              </span>

              <span className="block text-[10px] text-cg-muted leading-tight">
                نظام دعم القرار السريري
              </span>
            </div>

          </div>


          {/* User + Logout */}
          <div className="flex items-center gap-3">

            <div className="text-right hidden sm:block">
              <p className="text-xs font-medium text-white">
                {user?.name ?? 'مستخدم'}
              </p>

              <p className="text-[10px] text-cg-muted">
                مريض
              </p>
            </div>


            <div
              className="
                w-8 h-8
                rounded-full
                bg-indigo-600/30
                flex items-center justify-center
                text-xs font-bold
                text-indigo-300
              "
            >
              {user?.name?.charAt(0) ?? 'م'}
            </div>


            <button
              id="btn-patient-logout"
              type="button"
              onClick={logout}
              className="
                flex items-center gap-1.5
                text-xs text-cg-muted
                hover:text-red-400
                transition-colors
              "
              title="تسجيل الخروج"
              aria-label="تسجيل الخروج"
            >
              <LogOut className="w-4 h-4" />
            </button>

          </div>
        </div>
      </header>


      {/* ====================================================
          Main Content
      ==================================================== */}

      <main className="relative flex-1 px-4 py-8">

        <div className="max-w-2xl mx-auto space-y-6">


          {/* ==================================================
              Welcome Card
          ================================================== */}

          <InfoCard>

            <div className="flex items-center gap-4">

              <div
                className="
                  w-14 h-14
                  rounded-2xl
                  bg-emerald-500/15
                  border border-emerald-500/20
                  flex items-center justify-center
                  flex-shrink-0
                "
              >
                <Heart className="w-7 h-7 text-emerald-400" />
              </div>


              <div>
                <h1 className="text-xl font-bold text-white">
                  أهلاً وسهلاً،{' '}
                  {user?.name?.split(' ')[0] ?? 'مستخدم'} 👋
                </h1>

                <p className="text-sm text-cg-muted mt-1">
                  هذه بوابتك الصحية الشخصية.
                  يمكنك الاطلاع على نتائج تخطيط قلبك
                  وتوصيات فريقك الطبي بكل سهولة.
                </p>
              </div>

            </div>

          </InfoCard>


          {/* ==================================================
              Loading State
          ================================================== */}

          {loading && (
            <InfoCard>
              <div
                className="
                  flex items-center justify-center
                  gap-3 py-6
                  text-cg-muted
                "
              >
                <Loader2 className="w-5 h-5 animate-spin" />

                <span className="text-sm">
                  جارٍ تحميل تقريرك الطبي…
                </span>
              </div>
            </InfoCard>
          )}


          {/* ==================================================
              Error State
          ================================================== */}

          {error && !loading && (
            <InfoCard>
              <div className="flex items-center gap-3 text-red-400">

                <AlertCircle className="w-5 h-5 flex-shrink-0" />

                <p className="text-sm">
                  {error}
                </p>

              </div>
            </InfoCard>
          )}


          {/* ==================================================
              Report Section
          ================================================== */}

          {report && !loading && (
            <>

              {/* ==============================================
                  Status / Urgency Card
              ============================================== */}

              <InfoCard>

                <div className="flex items-start justify-between gap-4">

                  <div>
                    <p className="text-xs text-cg-muted mb-1">
                      حالة القلب الحالية
                    </p>

                    <h2 className="text-lg font-bold text-white">
                      {report.title}
                    </h2>

                    <p className="text-sm text-cg-muted mt-1 leading-relaxed whitespace-pre-line">
                      {report.summary}
                    </p>
                  </div>


                  <div
                    className={`
                      flex-shrink-0
                      px-3 py-1.5
                      rounded-full
                      border
                      text-xs font-semibold
                      ${urgency.colorClass}
                    `}
                  >
                    {urgency.label}
                  </div>

                </div>

              </InfoCard>


              {/* ==============================================
                  Reassurance Banner
              ============================================== */}

              {report.urgency_level === 'LOW' && (
                <InfoCard
                  className="
                    border-emerald-500/20
                    bg-emerald-500/5
                  "
                >
                  <div className="flex items-center gap-3">

                    <ShieldCheck className="w-6 h-6 text-emerald-400 flex-shrink-0" />

                    <div>
                      <p className="text-sm font-semibold text-emerald-300">
                        وضعك القلبي مستقر ✨
                      </p>

                      <p className="text-xs text-emerald-400/70 mt-0.5">
                        لم يتم الكشف عن أي أنماط غير طبيعية
                        في مخطط قلبك. استمر في اتباع
                        توصيات طبيبك.
                      </p>
                    </div>

                  </div>
                </InfoCard>
              )}


              {/* ==============================================
                  Emergency Banner
              ============================================== */}

              {report.urgency_level === 'CRITICAL' && (
                <InfoCard
                  className="
                    border-red-500/40
                    bg-red-500/10
                  "
                >
                  <div className="flex items-center gap-3">

                    <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 animate-pulse" />

                    <div>
                      <p className="text-sm font-bold text-red-300">
                        ⚠ يُرجى التواصل مع طبيبك فورًا
                      </p>

                      <p className="text-xs text-red-400/70 mt-0.5">
                        اكتشف النظام نمطًا يستوجب
                        المراجعة الطبية العاجلة.
                        لا تتأخر في طلب الرعاية.
                      </p>
                    </div>

                  </div>
                </InfoCard>
              )}


              {/* ==============================================
                  Recommendations
              ============================================== */}

              {report.recommendations.length > 0 && (
                <InfoCard>

                  <div className="flex items-center gap-2 mb-4">

                    <ClipboardList className="w-5 h-5 text-indigo-400" />

                    <h3 className="text-sm font-semibold text-white">
                      توصيات الفريق الطبي
                    </h3>

                  </div>


                  <ul className="space-y-3">

                    {report.recommendations.map(
                      (recommendation, index) => (
                        <li
                          key={`${recommendation}-${index}`}
                          className="flex items-start gap-3"
                        >

                          <span
                            className="
                              w-6 h-6
                              rounded-full
                              bg-indigo-600/20
                              border border-indigo-500/30
                              flex-shrink-0
                              flex items-center justify-center
                              text-xs font-bold
                              text-indigo-400
                            "
                          >
                            {index + 1}
                          </span>

                          <p className="text-sm text-cg-text leading-relaxed">
                            {recommendation}
                          </p>

                        </li>
                      ),
                    )}

                  </ul>

                </InfoCard>
              )}


              {/* ==============================================
                  Guidelines
              ============================================== */}

              {report.guidelines.length > 0 && (
                <InfoCard>

                  <div className="flex items-center gap-2 mb-3">

                    <ChevronLeft className="w-4 h-4 text-cg-muted" />

                    <h3 className="text-sm font-semibold text-white">
                      الإرشادات الطبية المرجعية
                      (AHA/ESC)
                    </h3>

                  </div>


                  <ul className="space-y-2">

                    {report.guidelines.map(
                      (guideline, index) => (
                        <li
                          key={`${guideline}-${index}`}
                          className="
                            text-xs
                            text-cg-muted
                            leading-relaxed
                            border-r-2
                            border-indigo-500/30
                            pr-3
                          "
                        >
                          {guideline}
                        </li>
                      ),
                    )}

                  </ul>

                </InfoCard>
              )}


              {/* ==============================================
                  Report Timestamp
              ============================================== */}

              <p className="text-center text-[11px] text-cg-muted">

                تاريخ إصدار التقرير:{' '}

                {new Date(
                  report.generated_at,
                ).toLocaleDateString(
                  'ar-SA',
                  {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  },
                )}

              </p>

            </>
          )}


          {/* ==================================================
              Footer
          ================================================== */}

          <p className="text-center text-[11px] text-cg-muted pb-4">
            كاردیوغارد AI · جميع البيانات مشفرة ومحمية ·
            هذا التقرير لأغراض إعلامية فقط
          </p>

        </div>
      </main>
    </div>
  );
}