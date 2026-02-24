<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, createReportSession, saveReportFormFields, uploadReportImage } from '@/api'
import ImageUploadField from '@/components/ImageUploadField.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import {
  useReportIntakeDraft,
  type UploadItem,
} from '@/composables/use-report-intake-draft'
import { PHOTO_GROUPS, type PhotoGroupConfig } from '@/constants/photo-groups'
import type { PhotoGroupName, ReportFormFields } from '@/types/report'
import { compressImageForUpload } from '@/utils/image-compression'

const router = useRouter()
const { confirmationReady, form, generatedDownloadUrl, selectionWarnings, sessionId, uploads } =
  useReportIntakeDraft()

const isSubmitting = ref(false)
const submitError = ref('')
const submitSuccess = ref('')

const fieldErrors = computed<Record<string, string>>(() => {
  const errors: Record<string, string> = {}

  if (!/^\d{4}-\d{2}$/.test(form.building_details.testing_date)) {
    errors.testing_date = 'Testing date is required.'
  }
  if (!form.building_details.building_name.trim()) {
    errors.building_name = 'Building name is required.'
  }
  if (!form.building_details.building_location.trim()) {
    errors.building_location = 'Building location is required.'
  }
  if (form.building_details.number_of_storey < 1) {
    errors.number_of_storey = 'Number of storey must be at least 1.'
  }

  if (form.superstructure.rebar_scanning.number_of_rebar_scan_locations < 1) {
    errors.number_of_rebar_scan_locations = 'Rebar scan locations must be at least 1.'
  }
  if (form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations < 1) {
    errors.number_of_rebound_hammer_test_locations =
      'Rebound hammer test locations must be at least 1.'
  }
  if (form.superstructure.concrete_core_extraction.number_of_coring_locations < 1) {
    errors.number_of_coring_locations = 'Coring locations must be at least 1.'
  }
  if (form.superstructure.rebar_extraction.number_of_rebar_samples_extracted < 1) {
    errors.number_of_rebar_samples_extracted = 'Rebar samples must be at least 1.'
  }
  if (!form.superstructure.restoration_works.non_shrink_grout_product_used.trim()) {
    errors.non_shrink_grout_product_used = 'Non-shrink grout product is required.'
  }
  if (!form.superstructure.restoration_works.epoxy_ab_used.trim()) {
    errors.epoxy_ab_used = 'Epoxy A&B product is required.'
  }

  if (form.substructure.concrete_core_extraction.number_of_foundation_locations < 1) {
    errors.number_of_foundation_locations = 'Foundation locations must be at least 1.'
  }
  if (form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted < 1) {
    errors.number_of_foundation_cores_extracted = 'Foundation cores extracted must be at least 1.'
  }

  if (!form.signature.prepared_by.trim()) {
    errors.prepared_by = 'Prepared by is required.'
  }
  if (!form.signature.prepared_by_role.trim()) {
    errors.prepared_by_role = 'Role is required.'
  }

  return errors
})

const missingPhotoGroupLabels = computed(() => {
  return PHOTO_GROUPS.filter((group) => uploads[group.name].length < group.min).map(
    (group) => group.label,
  )
})

const canSubmit = computed(() => {
  return (
    Object.keys(fieldErrors.value).length === 0 &&
    missingPhotoGroupLabels.value.length === 0 &&
    !isSubmitting.value
  )
})

function createItemId(): string {
  if (globalThis.crypto && 'randomUUID' in globalThis.crypto) {
    return globalThis.crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function releasePreviewUrls(items: UploadItem[]): void {
  for (const item of items) {
    URL.revokeObjectURL(item.previewUrl)
  }
}

function onFilesSelected(group: PhotoGroupConfig, files: File[]): void {
  releasePreviewUrls(uploads[group.name])

  const truncatedFiles = files.slice(0, group.max)
  uploads[group.name] = truncatedFiles.map((file) => ({
    id: createItemId(),
    name: file.name,
    file,
    previewUrl: URL.createObjectURL(file),
    status: 'pending',
    message: 'Queued',
    uploadedImage: null,
  }))

  selectionWarnings[group.name] =
    files.length > group.max
      ? `Only the first ${group.max} file(s) were kept for this group.`
      : ''
}

function photoGroupError(group: PhotoGroupConfig): string {
  if (uploads[group.name].length < group.min) {
    return `Add at least ${group.min} photo(s).`
  }

  return selectionWarnings[group.name]
}

function normalizeErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === 'string') {
      return error.detail
    }

    if (error.detail && typeof error.detail === 'object' && 'message' in error.detail) {
      const detail = error.detail as { message?: unknown }
      if (typeof detail.message === 'string') {
        return detail.message
      }
    }

    return `Request failed (${error.status}).`
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected error while uploading report data.'
}

function buildFormPayload(): ReportFormFields {
  return {
    building_details: {
      testing_date: form.building_details.testing_date,
      building_name: form.building_details.building_name.trim(),
      building_location: form.building_details.building_location.trim(),
      number_of_storey: form.building_details.number_of_storey,
    },
    superstructure: {
      rebar_scanning: {
        number_of_rebar_scan_locations: form.superstructure.rebar_scanning.number_of_rebar_scan_locations,
      },
      rebound_hammer_test: {
        number_of_rebound_hammer_test_locations:
          form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations,
      },
      concrete_core_extraction: {
        number_of_coring_locations: form.superstructure.concrete_core_extraction.number_of_coring_locations,
      },
      rebar_extraction: {
        number_of_rebar_samples_extracted:
          form.superstructure.rebar_extraction.number_of_rebar_samples_extracted,
      },
      restoration_works: {
        non_shrink_grout_product_used:
          form.superstructure.restoration_works.non_shrink_grout_product_used.trim(),
        epoxy_ab_used: form.superstructure.restoration_works.epoxy_ab_used.trim(),
      },
    },
    substructure: {
      concrete_core_extraction: {
        number_of_foundation_locations:
          form.substructure.concrete_core_extraction.number_of_foundation_locations,
        number_of_foundation_cores_extracted:
          form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted,
      },
    },
    signature: {
      prepared_by: form.signature.prepared_by.trim(),
      prepared_by_role: form.signature.prepared_by_role.trim(),
    },
  }
}

async function uploadGroupItem(
  currentSessionId: string,
  groupName: PhotoGroupName,
  item: UploadItem,
): Promise<void> {
  if (item.uploadedImage) {
    item.status = 'uploaded'
    item.message = 'Uploaded'
    return
  }

  try {
    item.status = 'compressing'
    item.message = 'Compressing...'
    const compressedFile = await compressImageForUpload(item.file)

    item.status = 'uploading'
    item.message = 'Uploading...'
    const uploadResult = await uploadReportImage(currentSessionId, groupName, compressedFile)

    item.uploadedImage = uploadResult.image
    item.status = 'uploaded'
    item.message = 'Uploaded'
  } catch (error) {
    item.status = 'error'
    item.message = normalizeErrorMessage(error)
    throw error
  }
}

async function submitIntake(): Promise<void> {
  if (!canSubmit.value) {
    return
  }

  isSubmitting.value = true
  submitError.value = ''
  submitSuccess.value = ''
  confirmationReady.value = false
  generatedDownloadUrl.value = null

  try {
    if (!sessionId.value) {
      const createdSession = await createReportSession()
      sessionId.value = createdSession.session_id
    }

    if (!sessionId.value) {
      throw new Error('Unable to initialize report session.')
    }

    await saveReportFormFields(sessionId.value, buildFormPayload())

    const uploadJobs: Promise<void>[] = []
    for (const group of PHOTO_GROUPS) {
      for (const item of uploads[group.name]) {
        uploadJobs.push(uploadGroupItem(sessionId.value, group.name, item))
      }
    }

    const uploadResults = await Promise.allSettled(uploadJobs)
    const failedUploads = uploadResults.filter(
      (result): result is PromiseRejectedResult => result.status === 'rejected',
    )

    if (failedUploads.length > 0) {
      throw new Error(
        `${failedUploads.length} photo upload${failedUploads.length === 1 ? '' : 's'} failed. ` +
          'Fix the items marked in red and retry.',
      )
    }

    submitSuccess.value = `Draft saved and photos uploaded. Session ${sessionId.value}.`
    confirmationReady.value = true
    void router.push({ name: 'confirmation' })
  } catch (error) {
    submitError.value = normalizeErrorMessage(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="intake-screen">
    <form class="intake-form" @submit.prevent="submitIntake">
      <header class="intake-hero">
        <p class="intake-hero__kicker">SBS Reportr</p>
        <h1 class="intake-hero__title">Activity Report Intake</h1>
        <p class="intake-hero__subtitle">
          Complete every field and upload every required photo group before proceeding to generation.
        </p>
      </header>

      <section class="form-panel">
        <SectionHeader title="Building Details" subtitle="Cover page and introduction values" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Testing Date</span>
            <input v-model="form.building_details.testing_date" class="field__input" type="month" />
            <span v-if="fieldErrors.testing_date" class="field__error">{{ fieldErrors.testing_date }}</span>
          </label>

          <label class="field">
            <span class="field__label">Building Name</span>
            <input v-model="form.building_details.building_name" class="field__input" maxlength="200" />
            <span v-if="fieldErrors.building_name" class="field__error">{{ fieldErrors.building_name }}</span>
          </label>

          <label class="field field--full">
            <span class="field__label">Building Location</span>
            <textarea
              v-model="form.building_details.building_location"
              class="field__input field__textarea"
              maxlength="500"
            />
            <span v-if="fieldErrors.building_location" class="field__error">{{ fieldErrors.building_location }}</span>
          </label>

          <label class="field">
            <span class="field__label">Number of Storey</span>
            <input
              v-model.number="form.building_details.number_of_storey"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_storey" class="field__error">{{ fieldErrors.number_of_storey }}</span>
          </label>
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="Superstructure" subtitle="B.1 to B.6 values" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Rebar Scan Locations</span>
            <input
              v-model.number="form.superstructure.rebar_scanning.number_of_rebar_scan_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_rebar_scan_locations" class="field__error">
              {{ fieldErrors.number_of_rebar_scan_locations }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Rebound Hammer Test Locations</span>
            <input
              v-model.number="form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_rebound_hammer_test_locations" class="field__error">
              {{ fieldErrors.number_of_rebound_hammer_test_locations }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Coring Locations</span>
            <input
              v-model.number="form.superstructure.concrete_core_extraction.number_of_coring_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_coring_locations" class="field__error">
              {{ fieldErrors.number_of_coring_locations }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Rebar Samples Extracted</span>
            <input
              v-model.number="form.superstructure.rebar_extraction.number_of_rebar_samples_extracted"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_rebar_samples_extracted" class="field__error">
              {{ fieldErrors.number_of_rebar_samples_extracted }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Non-shrink Grout Product</span>
            <input
              v-model="form.superstructure.restoration_works.non_shrink_grout_product_used"
              class="field__input"
              maxlength="200"
            />
            <span v-if="fieldErrors.non_shrink_grout_product_used" class="field__error">
              {{ fieldErrors.non_shrink_grout_product_used }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Epoxy A&B Product</span>
            <input
              v-model="form.superstructure.restoration_works.epoxy_ab_used"
              class="field__input"
              maxlength="200"
            />
            <span v-if="fieldErrors.epoxy_ab_used" class="field__error">{{ fieldErrors.epoxy_ab_used }}</span>
          </label>
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="Substructure and Signature" subtitle="C.1 values and sign-off" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Foundation Locations</span>
            <input
              v-model.number="form.substructure.concrete_core_extraction.number_of_foundation_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_foundation_locations" class="field__error">
              {{ fieldErrors.number_of_foundation_locations }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Extracted Foundation Cores</span>
            <input
              v-model.number="form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_foundation_cores_extracted" class="field__error">
              {{ fieldErrors.number_of_foundation_cores_extracted }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Prepared By</span>
            <input v-model="form.signature.prepared_by" class="field__input" maxlength="100" />
            <span v-if="fieldErrors.prepared_by" class="field__error">{{ fieldErrors.prepared_by }}</span>
          </label>

          <label class="field">
            <span class="field__label">Role</span>
            <input v-model="form.signature.prepared_by_role" class="field__input" maxlength="100" />
            <span v-if="fieldErrors.prepared_by_role" class="field__error">{{ fieldErrors.prepared_by_role }}</span>
          </label>
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader
          title="Photo Evidence"
          subtitle="Images are resized to max 1000px longest side and uploaded as JPEG quality 75"
        />

        <div class="upload-grid">
          <ImageUploadField
            v-for="group in PHOTO_GROUPS"
            :key="group.name"
            :label="group.label"
            :section="group.section"
            :min="group.min"
            :max="group.max"
            :items="uploads[group.name]"
            :disabled="isSubmitting"
            :error="photoGroupError(group)"
            @select="(files) => onFilesSelected(group, files)"
          />
        </div>

        <p v-if="missingPhotoGroupLabels.length > 0" class="form-summary form-summary--warning">
          Missing photo groups: {{ missingPhotoGroupLabels.join(', ') }}
        </p>
      </section>

      <footer class="form-actions">
        <button class="btn btn--primary" type="submit" :disabled="!canSubmit">
          {{ isSubmitting ? 'Saving draft and uploading photos...' : 'Continue to Confirmation' }}
        </button>
        <p class="form-summary">
          Continue unlocks only when all required fields and photo groups are valid.
        </p>
        <p v-if="submitError" class="form-summary form-summary--error">{{ submitError }}</p>
        <p v-if="submitSuccess" class="form-summary form-summary--success">{{ submitSuccess }}</p>
        <p v-if="sessionId" class="form-summary form-summary--mono">Session ID: {{ sessionId }}</p>
      </footer>
    </form>
  </main>
</template>

<style scoped>
.intake-screen {
  min-height: 100vh;
  padding: 2.5rem 1rem 4rem;
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--orange) 16%, transparent), transparent 35%),
    linear-gradient(150deg, #f0f3fb 0%, #f7f9fc 45%, #eef5ff 100%);
}

.intake-form {
  width: min(1200px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 1.25rem;
}

.intake-hero {
  padding: 1.5rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
}

.intake-hero__kicker {
  margin: 0;
  font: 700 0.72rem/1.4 var(--font-mono);
  color: var(--orange);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.intake-hero__title {
  margin: 0.2rem 0 0.45rem;
  font: 700 2rem/1.1 var(--font-display);
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.intake-hero__subtitle {
  margin: 0;
  color: var(--muted);
}

.form-panel {
  padding: 1.1rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
}

.field-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.field {
  display: grid;
  gap: 0.35rem;
}

.field--full {
  grid-column: 1 / -1;
}

.field__label {
  font: 600 0.83rem/1.3 var(--font-body);
  color: var(--ink);
}

.field__input {
  width: 100%;
  padding: 0.58rem 0.65rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  color: var(--ink);
  font: 500 0.95rem/1.4 var(--font-body);
}

.field__input:focus {
  outline: 2px solid color-mix(in srgb, var(--orange) 35%, transparent);
  border-color: var(--orange);
}

.field__textarea {
  min-height: 90px;
  resize: vertical;
}

.field__error {
  color: #b42318;
  font: 500 0.76rem/1.3 var(--font-body);
}

.upload-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.form-actions {
  display: grid;
  gap: 0.5rem;
  padding: 1.2rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
}

.btn {
  border: 0;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  font: 700 0.95rem/1 var(--font-body);
  cursor: pointer;
}

.btn--primary {
  color: #fff;
  background: linear-gradient(95deg, var(--orange) 0%, #ff6d2f 100%);
}

.btn--primary:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.form-summary {
  margin: 0;
  color: var(--muted);
  font-size: 0.86rem;
}

.form-summary--warning {
  color: #7a2e0a;
}

.form-summary--error {
  color: #b42318;
}

.form-summary--success {
  color: #067647;
}

.form-summary--mono {
  font-family: var(--font-mono);
  color: var(--navy);
}

@media (max-width: 700px) {
  .intake-screen {
    padding: 1rem 0.75rem 2rem;
  }

  .intake-hero__title {
    font-size: 1.7rem;
  }
}
</style>
