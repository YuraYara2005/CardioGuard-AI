import { useState, useEffect } from 'react';

import { useAuth } from '../store/AuthContext';

import {
  Heart,
  ShieldCheck,
  AlertCircle,
  LogOut,
  Activity,
  Loader2,
  FileText,
} from 'lucide-react';

interface StoredPatientReport {
  patient_id: string;
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
  doctor_report: string;
  patient_report: string;
  generated_at: string;
}

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

export default function PatientPortal() {
  const { user, logout } = useAuth();

  const [report, setReport] =
    useState<StoredPatientReport | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    function loadSavedReport() {
      try {
        setLoading(true);
        setError('');

        const patientId = user?.patientId;

        if (!patientId) {
          setError(
            'تعذر تحديد ملف المريض المرتبط بهذا الحساب.',
          );
          return;
        }

        const raw = localStorage.getItem(
          `cg_patient_report_${patientId}`,
        );

        if (!raw) {
          setReport(null);
          return;
        }

        const parsed =
          JSON.parse(raw) as StoredPatientReport;

        if (parsed.patient_id !== patientId) {
          setError(
            'تعذر تحميل التقرير المرتبط بهذا الحساب.',
          );
          return;
        }

        setReport(parsed);
      } catch (err) {
        console.error(
          '[PatientPortal] Failed to load saved report:',
          err,
        );

        setError(
          'تعذر تحميل التقرير الطبي حاليًا.',
        );
      } finally {
        setLoading(false);
      }
    }

    loadSavedReport();
  }, [user?.patientId]);

  return (
    <div
      dir="rtl"
      lang="ar"
      className="min-h-screen bg-cg-bg flex flex-col"
      style={{
        fontFamily:
          "'Segoe UI', 'Arial', sans-serif",
      }}
    >
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-indigo-600/8 rounded-full blur-3xl" />
        <div className="absolute -bottom-32 -left-32 w-80 h-80 bg-emerald-500/8 rounded-full blur-3xl" />
      </div>

      <header className="relative border-b border-cg-border bg-cg-surface/60 backdrop-blur-md px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <Activity className="w-5 h-5 text-indigo-400" />
            </div>

            <div>
              <span className="block text-sm font-bold text-white leading-tight">
                كارديوغارد AI
              </span>

              <span className="block text-[10px] text-cg-muted leading-tight">
                نظام دعم القرار السريري
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-medium text-white">
                {user?.name ?? 'مستخدم'}
              </p>

              <p className="text-[10px] text-cg-muted">
                مريض · {user?.patientId ?? ''}
              </p>
            </div>

            <div className="w-8 h-8 rounded-full bg-indigo-600/30 flex items-center justify-center text-xs font-bold text-indigo-300">
              {user?.name?.charAt(0) ?? 'م'}
            </div>

            <button
              id="btn-patient-logout"
              type="button"
              onClick={logout}
              className="flex items-center gap-1.5 text-xs text-cg-muted hover:text-red-400 transition-colors"
              title="تسجيل الخروج"
              aria-label="تسجيل الخروج"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="relative flex-1 px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-6">
          <InfoCard>
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                <Heart className="w-7 h-7 text-emerald-400" />
              </div>

              <div>
                <h1 className="text-xl font-bold text-white">
                  أهلاً وسهلاً،{' '}
                  {user?.name?.split(' ')[0] ?? 'مستخدم'} 👋
                </h1>

                <p className="text-sm text-cg-muted mt-1">
                  هذه بوابتك الصحية الشخصية.
                  يمكنك الاطلاع على آخر تقرير قلبي
                  تم إنشاؤه بواسطة فريقك الطبي.
                </p>
              </div>
            </div>
          </InfoCard>

          {loading && (
            <InfoCard>
              <div className="flex items-center justify-center gap-3 py-6 text-cg-muted">
                <Loader2 className="w-5 h-5 animate-spin" />

                <span className="text-sm">
                  جارٍ تحميل تقريرك الطبي…
                </span>
              </div>
            </InfoCard>
          )}

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

          {!loading && !error && !report && (
            <InfoCard>
              <div className="text-center py-6">
                <FileText className="w-10 h-10 text-cg-muted mx-auto mb-3" />

                <h2 className="text-white font-semibold">
                  لا يوجد تقرير طبي حتى الآن
                </h2>

                <p className="text-sm text-cg-muted mt-2">
                  سيظهر تقريرك هنا بعد أن يقوم الطبيب
                  بإجراء التحليل وإنشاء التقرير السريري.
                </p>
              </div>
            </InfoCard>
          )}

          {report && !loading && (
            <>
              <InfoCard>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs text-cg-muted mb-1">
                      نتيجة التحليل القلبي
                    </p>

                    <h2 className="text-lg font-bold text-white">
                      {report.diagnosis}
                    </h2>

                    <p className="text-xs text-cg-muted mt-2">
                      دقة النموذج:{' '}
                      {(report.confidence_score * 100).toFixed(1)}%
                    </p>
                  </div>

                  <div
                    className={`
                      flex-shrink-0
                      px-3 py-1.5
                      rounded-full
                      border
                      text-xs font-semibold
                      ${report.is_emergency
                        ? 'text-red-400 bg-red-500/10 border-red-500/30'
                        : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                      }
                    `}
                  >
                    {report.is_emergency
                      ? 'حالة عاجلة'
                      : 'متابعة مستقرة'}
                  </div>
                </div>
              </InfoCard>

              {report.is_emergency ? (
                <InfoCard className="border-red-500/40 bg-red-500/10">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 animate-pulse" />

                    <div>
                      <p className="text-sm font-bold text-red-300">
                        ⚠ يُرجى التواصل مع طبيبك فورًا
                      </p>

                      <p className="text-xs text-red-400/70 mt-0.5">
                        اكتشف النظام نمطًا يستوجب
                        المراجعة الطبية العاجلة.
                      </p>
                    </div>
                  </div>
                </InfoCard>
              ) : (
                <InfoCard className="border-emerald-500/20 bg-emerald-500/5">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="w-6 h-6 text-emerald-400 flex-shrink-0" />

                    <div>
                      <p className="text-sm font-semibold text-emerald-300">
                        لا توجد إشارة طوارئ حالية ✨
                      </p>

                      <p className="text-xs text-emerald-400/70 mt-0.5">
                        استمر في اتباع تعليمات ومتابعة طبيبك.
                      </p>
                    </div>
                  </div>
                </InfoCard>
              )}

              <InfoCard>
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-emerald-400" />

                  <h3 className="text-sm font-semibold text-white">
                    تقريرك الطبي
                  </h3>
                </div>

                <div className="text-sm text-cg-text leading-relaxed whitespace-pre-wrap">
                  {report.patient_report}
                </div>
              </InfoCard>

              <p className="text-center text-[11px] text-cg-muted">
                تاريخ إصدار التقرير:{' '}

                {new Date(
                  report.generated_at,
                ).toLocaleDateString(
                  'ar-EG',
                  {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  },
                )}
              </p>
            </>
          )}

          <p className="text-center text-[11px] text-cg-muted pb-4">
            كارديوغارد AI · جميع البيانات مشفرة ومحمية ·
            هذا التقرير لأغراض إعلامية فقط
          </p>
        </div>
      </main>
    </div>
  );
}