import {
  useState,
  useEffect,
  type DragEvent,
  type ChangeEvent,
} from 'react';

import {
  Upload,
  FileCode2,
  ImagePlus,
  User,
  CheckCircle2,
  Loader2,
  AlertCircle,
  ChevronRight,
  Activity,
  FlaskConical,
} from 'lucide-react';

import {
  predictMultimodal,
  getPatients,
  type MultimodalPredictionResponse,
} from '../api/patientService';
import type { Patient } from '../types';


// ============================================================
// Props
// ============================================================

interface NewAnalysisTabProps {
  onResult: (result: MultimodalPredictionResponse) => void;
}


// ============================================================
// Form Types
// ============================================================

interface FormState {
  patientId: string;
  ecgFile: File | null;
  ecgImage: File | null;

  age: string;
  bloodPressure: string;
  heartRate: string;
  sex: string;

  symptoms: string[];

  troponin: string;
  ckMb: string;
  bnp: string;
  creatinine: string;
  hba1c: string;
}


// ============================================================
// Constants
// ============================================================

const SYMPTOM_OPTIONS = [
  'Chest Pain',
  'Shortness of Breath',
  'Palpitations',
  'Dizziness',
  'Fatigue',
];

const INITIAL_FORM: FormState = {
  patientId: '',
  ecgFile: null,
  ecgImage: null,

  age: '',
  bloodPressure: '',
  heartRate: '',
  sex: '',

  symptoms: [],

  troponin: '',
  ckMb: '',
  bnp: '',
  creatinine: '',
  hba1c: '',
};


// ============================================================
// Drop Zone
// ============================================================

function DropZone({
  id,
  label,
  accept,
  icon: Icon,
  file,
  onFile,
}: {
  id: string;
  label: string;
  accept: string;
  icon: React.ElementType;
  file: File | null;
  onFile: (file: File) => void;
}) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(
    event: DragEvent<HTMLDivElement>,
  ) {
    event.preventDefault();
    setDragging(false);

    const file =
      event.dataTransfer.files?.[0];

    if (file) {
      onFile(file);
    }
  }

  return (
    <div
      id={`dropzone-${id}`}
      onDragEnter={() => setDragging(true)}
      onDragLeave={() => setDragging(false)}
      onDragOver={(event) =>
        event.preventDefault()
      }
      onDrop={handleDrop}
      onClick={() =>
        document
          .getElementById(`file-input-${id}`)
          ?.click()
      }
      className={`
        relative
        flex flex-col
        items-center
        justify-center
        gap-3
        p-8
        rounded-2xl
        border-2
        border-dashed
        cursor-pointer
        transition-all
        duration-200

        ${dragging
          ? 'border-indigo-500 bg-indigo-500/10'
          : file
            ? 'border-emerald-500/50 bg-emerald-500/5'
            : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'
        }
      `}
    >
      <input
        id={`file-input-${id}`}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(
          event: ChangeEvent<HTMLInputElement>,
        ) => {
          const file =
            event.target.files?.[0];

          if (file) {
            onFile(file);
          }
        }}
      />

      {file ? (
        <>
          <CheckCircle2 className="w-8 h-8 text-emerald-400" />

          <p className="
            text-xs
            text-emerald-400
            font-medium
            text-center
            truncate
            max-w-full
            px-2
          ">
            {file.name}
          </p>

          <p className="text-[10px] text-cg-muted">
            {(file.size / 1024).toFixed(1)} KB
            {' · '}
            Click to replace
          </p>
        </>
      ) : (
        <>
          <div className="
            w-12
            h-12
            rounded-2xl
            bg-white/5
            flex
            items-center
            justify-center
          ">
            <Icon className="w-6 h-6 text-cg-muted" />
          </div>

          <div className="text-center">
            <p className="text-sm font-medium text-white">
              {label}
            </p>

            <p className="text-xs text-cg-muted mt-0.5">
              Drag & drop or click to browse
            </p>
          </div>

          <Upload className="w-4 h-4 text-cg-muted" />
        </>
      )}
    </div>
  );
}


// ============================================================
// Main Component
// ============================================================

export default function NewAnalysisTab({
  onResult,
}: NewAnalysisTabProps) {
  const [form, setForm] =
    useState<FormState>(INITIAL_FORM);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState('');

  const [warning, setWarning] =
    useState('');

  const [patients, setPatients] = useState<Patient[]>([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [patientsError, setPatientsError] = useState('');

  useEffect(() => {
    async function loadPatients() {
      setLoadingPatients(true);
      try {
        const data = await getPatients();
        setPatients(data);
      } catch (err) {
        setPatientsError('Could not load patient registry.');
      } finally {
        setLoadingPatients(false);
      }
    }
    loadPatients();
  }, []);

  function handlePatientChange(patientId: string) {
    setForm((prev) => {
      const selected = patients.find((p) => p.id === patientId);
      if (!selected) {
        return { ...prev, patientId, age: '', sex: '' };
      }
      return {
        ...prev,
        patientId,
        age: selected.age.toString(),
        sex: selected.gender === 'Female' ? 'Female' : 'Male',
      };
    });
  }


  // ==========================================================
  // Generic Field Update
  // ==========================================================

  function updateField<K extends keyof FormState>(
    key: K,
    value: FormState[K],
  ) {
    setForm((previous) => ({
      ...previous,
      [key]: value,
    }));
  }


  // ==========================================================
  // Parse ECG JSON
  // ==========================================================

  async function parseECGFile(
    file: File,
  ): Promise<number[] | number[][]> {
    const text = await file.text();

    let parsed: unknown;

    try {
      parsed = JSON.parse(text);
    } catch {
      throw new Error(
        'ECG file contains invalid JSON.',
      );
    }

    if (Array.isArray(parsed)) {
      return parsed as number[] | number[][];
    }

    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'leads_data' in parsed
    ) {
      const value = (
        parsed as {
          leads_data: unknown;
        }
      ).leads_data;

      if (Array.isArray(value)) {
        return value as number[] | number[][];
      }
    }

    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'leads' in parsed
    ) {
      const value = (
        parsed as {
          leads: unknown;
        }
      ).leads;

      if (Array.isArray(value)) {
        return value as number[] | number[][];
      }
    }

    throw new Error(
      'ECG JSON must be an array, { "leads_data": [...] }, or { "leads": [...] }.',
    );
  }


  // ==========================================================
  // Convert ECG Image -> 224 x 224 x 3
  // ==========================================================

  async function imageFileToArray(
    file: File,
  ): Promise<number[][][]> {
    if (!file.type.startsWith('image/')) {
      throw new Error(
        'ECG image must be JPG, JPEG, PNG, or another browser-supported image format.',
      );
    }

    const objectUrl =
      URL.createObjectURL(file);

    try {
      const image =
        await new Promise<HTMLImageElement>(
          (resolve, reject) => {
            const img = new Image();

            img.onload = () =>
              resolve(img);

            img.onerror = () =>
              reject(
                new Error(
                  'Unable to read ECG image.',
                ),
              );

            img.src = objectUrl;
          },
        );

      const canvas =
        document.createElement('canvas');

      canvas.width = 224;
      canvas.height = 224;

      const context =
        canvas.getContext('2d');

      if (!context) {
        throw new Error(
          'Browser could not create image-processing canvas.',
        );
      }

      context.drawImage(
        image,
        0,
        0,
        224,
        224,
      );

      const imageData =
        context.getImageData(
          0,
          0,
          224,
          224,
        );

      const result: number[][][] = [];

      for (let y = 0; y < 224; y += 1) {
        const row: number[][] = [];

        for (let x = 0; x < 224; x += 1) {
          const index =
            (y * 224 + x) * 4;

          const red =
            imageData.data[index];

          const green =
            imageData.data[index + 1];

          const blue =
            imageData.data[index + 2];

          /*
           * IMPORTANT:
           * Send raw RGB values 0..255.
           *
           * Do not divide by 255 here unless the ML team's
           * notebook explicitly normalized images before
           * image_feature_extractor.keras.
           */
          row.push([
            red,
            green,
            blue,
          ]);
        }

        result.push(row);
      }

      return result;
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  }


  // ==========================================================
  // Symptom Toggle
  // ==========================================================

  function toggleSymptom(
    symptom: string,
  ) {
    setForm((previous) => {
      const alreadySelected =
        previous.symptoms.includes(symptom);

      return {
        ...previous,

        symptoms: alreadySelected
          ? previous.symptoms.filter(
            (item) => item !== symptom,
          )
          : [
            ...previous.symptoms,
            symptom,
          ],
      };
    });
  }


  // ==========================================================
  // Validation
  // ==========================================================

  function validateForm(): void {
    if (!form.patientId) {
      throw new Error(
        'Please select a registered patient.',
      );
    }

    if (!form.ecgFile) {
      throw new Error(
        'Please upload an ECG JSON file.',
      );
    }

    if (!form.ecgImage) {
      throw new Error(
        'Please upload an ECG image.',
      );
    }

    if (!form.age) {
      throw new Error(
        'Age is required.',
      );
    }

    if (!form.bloodPressure) {
      throw new Error(
        'Blood pressure is required.',
      );
    }

    if (!form.heartRate) {
      throw new Error(
        'Heart rate is required.',
      );
    }

    if (!form.sex) {
      throw new Error(
        'Sex is required.',
      );
    }

    if (!form.troponin) {
      throw new Error(
        'Troponin value is required.',
      );
    }

    if (!form.ckMb) {
      throw new Error(
        'CK-MB value is required.',
      );
    }

    if (!form.bnp) {
      throw new Error(
        'BNP value is required.',
      );
    }

    if (!form.creatinine) {
      throw new Error(
        'Creatinine value is required.',
      );
    }

    if (!form.hba1c) {
      throw new Error(
        'HbA1c value is required.',
      );
    }
  }


  // ==========================================================
  // Submit
  // ==========================================================

  async function handleSubmit() {
    setError('');
    setWarning('');

    try {
      validateForm();

      setLoading(true);

      const leadsData =
        await parseECGFile(
          form.ecgFile!,
        );

      // ── ECG shape validation ──────────────────────────────────────────
      // Reject obviously-too-small inputs. The backend predictor pads
      // short arrays to 1000 timesteps, but fewer than 100 samples of
      // real ECG data produces meaningless inference output.
      //
      // Valid shapes accepted by the backend:
      //   (1000, 12) — standard PTB-XL 100 Hz
      //   (12, 1000) — transposed; predictor auto-corrects
      //   flat list divisible by 12, length ≥ 1200 (100 × 12)
      const MIN_TIMESTEPS = 100;
      const MIN_FLAT_LENGTH = MIN_TIMESTEPS * 12; // 1200

      const firstItem = leadsData[0];
      const is2D = Array.isArray(firstItem);

      if (is2D) {
        const rows = leadsData.length;
        const cols = (firstItem as number[]).length;
        const timesteps = cols === 12 ? rows : cols === rows ? cols : rows;
        if (timesteps < MIN_TIMESTEPS) {
          throw new Error(
            `ECG array has only ${timesteps} timestep(s). ` +
            `A minimum of ${MIN_TIMESTEPS} timesteps (preferably 1000) ` +
            `are required for valid inference. ` +
            `Please upload a real PTB-XL or compatible 12-lead ECG recording.`,
          );
        }
      } else {
        // Flat array — must be at least 1200 floats
        const flatLen = leadsData.length;
        if (flatLen < MIN_FLAT_LENGTH) {
          throw new Error(
            `Flat ECG array length is ${flatLen}. ` +
            `Minimum required: ${MIN_FLAT_LENGTH} values (${MIN_TIMESTEPS} timesteps × 12 leads). ` +
            `Please upload a real 12-lead ECG recording, not a toy sample.`,
          );
        }
      }
      // ── End ECG validation ────────────────────────────────────────────

      const imageData =
        await imageFileToArray(
          form.ecgImage!,
        );

      const age =
        Number(form.age);

      const bloodPressure =
        Number(form.bloodPressure);

      const heartRate =
        Number(form.heartRate);

      const troponin =
        Number(form.troponin);

      const ckMb =
        Number(form.ckMb);

      const bnp =
        Number(form.bnp);

      const creatinine =
        Number(form.creatinine);

      const hba1c =
        Number(form.hba1c);

      const numericValues = [
        age,
        bloodPressure,
        heartRate,
        troponin,
        ckMb,
        bnp,
        creatinine,
        hba1c,
      ];

      if (
        numericValues.some(
          (value) => !Number.isFinite(value),
        )
      ) {
        throw new Error(
          'All numeric fields must contain valid numbers.',
        );
      }

      setWarning(
        'Running multimodal fusion inference. This may take a moment.',
      );

      const response =
        await predictMultimodal({
          patient_id: form.patientId,
          leads_data: leadsData,

          image_data: imageData,

          labs: {
            troponin,
            'ck-mb': ckMb,
            bnp,
            creatinine,
            hba1c,
          },

          age,
          blood_pressure: bloodPressure,
          heart_rate: heartRate,
          sex: form.sex,
          symptoms: form.symptoms,
        });

      setWarning('');

      onResult(response);
    } catch (err: unknown) {
      setWarning('');

      setError(
        err instanceof Error
          ? err.message
          : 'Multimodal analysis failed.',
      );
    } finally {
      setLoading(false);
    }
  }


  // ==========================================================
  // Render
  // ==========================================================

  return (
    <div className="space-y-6 animate-fade-in-up">

      {/* Header */}

      <div>
        <h2 className="text-lg font-semibold text-white">
          New Multi-Modal Analysis
        </h2>

        <p className="text-sm text-cg-muted mt-0.5">
          ECG signal + ECG image + laboratory values +
          patient metadata → multimodal fusion inference.
        </p>
      </div>


      {/* Error */}

      {error && (
        <div className="
          flex
          items-center
          gap-2
          text-red-400
          bg-red-500/10
          border
          border-red-500/20
          rounded-xl
          px-4
          py-3
          text-sm
        ">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}


      {/* Warning */}

      {warning && (
        <div className="
          flex
          items-center
          gap-2
          text-amber-400
          bg-amber-500/10
          border
          border-amber-500/20
          rounded-xl
          px-4
          py-3
          text-sm
        ">
          <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
          {warning}
        </div>
      )}


      {/* Uploads */}

      <div className="
        grid
        grid-cols-1
        md:grid-cols-2
        gap-4
      ">

        <div>
          <p className="
            text-xs
            font-semibold
            text-cg-muted
            uppercase
            tracking-wide
            mb-2
          ">
            1 · ECG Array Data
          </p>

          <DropZone
            id="ecg-array"
            label="ECG Signal (.json)"
            accept=".json"
            icon={FileCode2}
            file={form.ecgFile}
            onFile={(file) =>
              updateField(
                'ecgFile',
                file,
              )
            }
          />
        </div>


        <div>
          <p className="
            text-xs
            font-semibold
            text-cg-muted
            uppercase
            tracking-wide
            mb-2
          ">
            2 · ECG Image
          </p>

          <DropZone
            id="ecg-image"
            label="ECG Image (.jpg / .png)"
            accept="image/*"
            icon={ImagePlus}
            file={form.ecgImage}
            onFile={(file) =>
              updateField(
                'ecgImage',
                file,
              )
            }
          />
        </div>

      </div>


      {/* Laboratory Values */}

      <div className="glass-card p-6">
        <p className="
          text-xs
          font-semibold
          text-cg-muted
          uppercase
          tracking-wide
          mb-4
          flex
          items-center
          gap-2
        ">
          <FlaskConical className="w-4 h-4" />
          Laboratory Values
        </p>

        <div className="
          grid
          grid-cols-1
          sm:grid-cols-2
          lg:grid-cols-5
          gap-4
        ">

          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              Troponin *
            </label>

            <input
              type="number"
              step="any"
              value={form.troponin}
              onChange={(event) =>
                updateField(
                  'troponin',
                  event.target.value,
                )
              }
              className="input-field"
            />
          </div>


          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              CK-MB *
            </label>

            <input
              type="number"
              step="any"
              value={form.ckMb}
              onChange={(event) =>
                updateField(
                  'ckMb',
                  event.target.value,
                )
              }
              className="input-field"
            />
          </div>


          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              BNP *
            </label>

            <input
              type="number"
              step="any"
              value={form.bnp}
              onChange={(event) =>
                updateField(
                  'bnp',
                  event.target.value,
                )
              }
              className="input-field"
            />
          </div>


          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              Creatinine *
            </label>

            <input
              type="number"
              step="any"
              value={form.creatinine}
              onChange={(event) =>
                updateField(
                  'creatinine',
                  event.target.value,
                )
              }
              className="input-field"
            />
          </div>


          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              HbA1c *
            </label>

            <input
              type="number"
              step="any"
              value={form.hba1c}
              onChange={(event) =>
                updateField(
                  'hba1c',
                  event.target.value,
                )
              }
              className="input-field"
            />
          </div>

        </div>
      </div>


      {/* Metadata */}

      <div className="glass-card p-6">
        <p className="
          text-xs
          font-semibold
          text-cg-muted
          uppercase
          tracking-wide
          mb-4
          flex
          items-center
          gap-2
        ">
          <User className="w-4 h-4" />
          Patient Metadata
        </p>

        <div className="
          grid
          grid-cols-1
          sm:grid-cols-2
          gap-4
        ">

          {/* Patient Selection Dropdown */}
          <div className="sm:col-span-2 mb-2">
            <label className="block text-xs text-cg-muted mb-1.5">
              Registered Patient *
            </label>
            <div className="relative">
              <select
                value={form.patientId}
                onChange={(e) => handlePatientChange(e.target.value)}
                disabled={loadingPatients}
                className="input-field w-full appearance-none pr-10"
              >
                <option value="">
                  {loadingPatients ? 'Loading patients...' : 'Select a patient...'}
                </option>
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.id} — {p.name}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-cg-muted">
                <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20">
                  <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                </svg>
              </div>
            </div>
            {patientsError && (
              <p className="text-red-400 text-xs mt-1">{patientsError}</p>
            )}
          </div>

          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              Age *
            </label>

            <input
              type="number"
              min={0}
              max={130}
              value={form.age}
              onChange={(event) =>
                updateField(
                  'age',
                  event.target.value,
                )
              }
              className="input-field"
              placeholder="52"
            />
          </div>


          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              Sex *
            </label>

            <select
              value={form.sex}
              onChange={(event) =>
                updateField(
                  'sex',
                  event.target.value,
                )
              }
              className="input-field"
            >
              <option value="">
                Select…
              </option>

              <option value="Female">
                Female
              </option>

              <option value="Male">
                Male
              </option>
            </select>
          </div>


          <div>
            <label className="block text-xs text-cg-muted mb-1.5">
              Blood Pressure *
            </label>

            <input
              type="number"
              value={form.bloodPressure}
              onChange={(event) =>
                updateField(
                  'bloodPressure',
                  event.target.value,
                )
              }
              className="input-field"
              placeholder="120"
            />
          </div>


          <div>
            <label className="
              block
              text-xs
              text-cg-muted
              mb-1.5
            ">
              Heart Rate *
            </label>

            <div className="relative">
              <Activity className="
                absolute
                left-3
                top-1/2
                -translate-y-1/2
                w-4
                h-4
                text-cg-muted
              " />

              <input
                type="number"
                value={form.heartRate}
                onChange={(event) =>
                  updateField(
                    'heartRate',
                    event.target.value,
                  )
                }
                className="input-field pl-10"
                placeholder="75"
              />
            </div>
          </div>

        </div>


        {/* Symptoms */}

        <div className="mt-5">
          <label className="
            block
            text-xs
            text-cg-muted
            mb-2
          ">
            Symptoms
          </label>

          <div className="
            flex
            flex-wrap
            gap-2
          ">
            {SYMPTOM_OPTIONS.map(
              (symptom) => {
                const selected =
                  form.symptoms.includes(symptom);

                return (
                  <button
                    key={symptom}
                    type="button"
                    onClick={() =>
                      toggleSymptom(symptom)
                    }
                    className={`
                      px-3
                      py-2
                      rounded-xl
                      text-xs
                      border
                      transition-all

                      ${selected
                        ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                        : 'bg-white/[0.02] border-white/10 text-cg-muted hover:border-white/20'
                      }
                    `}
                  >
                    {symptom}
                  </button>
                );
              },
            )}
          </div>
        </div>

      </div>


      {/* Submit */}

      <div className="flex justify-end">
        <button
          id="btn-run-analysis"
          type="button"
          onClick={handleSubmit}
          disabled={loading}
          className="btn-primary"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}

          {loading
            ? 'Running Fusion Analysis…'
            : 'Run Multi-Modal Analysis'}
        </button>
      </div>

    </div>
  );
}